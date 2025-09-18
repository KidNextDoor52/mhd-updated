from fastapi import APIRouter, Request, UploadFile, File, Depends, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone
from bson import ObjectId
import os
from typing import List, Optional
import csv, io, re
from bson.errors import InvalidId
from app.db import db
from app.auth import get_current_user, get_current_user_optional 
from app.utils.logger import log_activity
from app.utils.ocr import extract_text_from_pdf_or_ocr, ocr_image_path


router = APIRouter(prefix="/upload", tags=["upload"])
templates = Jinja2Templates(directory="app/templates")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

uploads_collection = db.uploads
upload_flags = db.upload_flags
shared_links = db.shared_links

medical_history = db.medical_history
equipment_col = db.equipment
weightroom_col = db.weightroom
training_col = db.training


# ----------------- time helpers -----------------
def _utcnow():
    return datetime.now(timezone.utc)


# ----------------- string/number helpers -----------------
def _norm(s: Optional[str]) -> str:
    return (s or "").strip()

def _key(s: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

def _safe_int(s: Optional[str]) -> Optional[int]:
    try:
        return int(float(_norm(s))) if _norm(s) != "" else None
    except Exception:
        return None

def _safe_float(s: Optional[str]) -> Optional[float]:
    try:
        return float(_norm(s)) if _norm(s) != "" else None
    except Exception:
        return None

def _guess_bool(s: Optional[str]) -> Optional[bool]:
    v = _norm(s).lower()
    if v in {"yes", "y", "true", "t", "1"}:
        return True
    if v in {"no", "n", "false", "f", "0"}:
        return False
    return None

_num_re = re.compile(r"-?\d+(?:\.\d+)?")

def _safe_float_loose(s: Optional[str]) -> Optional[float]:
    """
    Extracts the first number from a string like '225 lbs' or '4.57s'.
    Returns None if no number is found.
    """
    if s is None:
        return None
    m = _num_re.search(str(s))
    return float(m.group()) if m else None

_feet_inches_re = re.compile(
    r"^\s*(\d+)\s*(?:'|ft|feet)\s*(\d+)?\s*(?:\"|in|inch|inches)?\s*$",
    re.I
)

def _parse_inches(s: Optional[str]) -> Optional[float]:
    """
    Parses 9' 10", 9ft 10in, 5'11", etc. Falls back to _safe_float_loose.
    Returns total inches as a float.
    """
    if s is None:
        return None
    st = str(s).strip()
    m = _feet_inches_re.match(st)
    if m:
        feet = int(m.group(1))
        inches = int(m.group(2) or 0)
        return feet * 12 + inches
    # If it's like "118 in" or "30", just pull the first number
    return _safe_float_loose(st)

_PLACEHOLDER_RE = re.compile(r"^\s*(\{\{.*\}\}|\[\[.*\]\]|<.*>|n/?a|n\.a\.|none|null|-+)\s*$", re.I)

def _clean_text(v: str | None) -> str | None:
    if v is None:
        return None
    s = _norm(str(v))
    # 🔧 use .match(), not call the pattern
    if not s or _PLACEHOLDER_RE.match(s):
        return None
    return s

# ----------------- file helpers -----------------
def _ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()

def validate_upload(filename: str, size_bytes: int, categories: List[str]) -> List[str]:
    errs: List[str] = []
    ext = _ext(filename)
    allowed = {".csv", ".txt", ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    if ext not in allowed:
        errs.append(f"Unsupported file type {ext}. Allowed: {', '.join(sorted(allowed))}")
    if size_bytes <= 0:
        errs.append("File is empty.")
    if not categories:
        errs.append("Please select at least one category (Medical / Performance / Equipment).")
    return errs

def validate_shared_download(file_meta: dict, token: Optional[str], email: Optional[str]):
    """
    Validates that a shared download is allowed for this file, token and email.
    Mirrors the logic used by /share.
    """
    if not token or not email:
        raise HTTPException(status_code=403, detail="Share token and email required")

    link = shared_links.find_one({"token": token})
    if not link:
        raise HTTPException(status_code=404, detail="Invalid link")
    if link["expires_at"] < _utcnow():
        raise HTTPException(status_code=410, detail="Link expired")
    if email.lower() != link["recipient_email"]:
        raise HTTPException(status_code=403, detail="Email not authorized for this link")

    # Owner must match
    if link["owner"] != file_meta["username"]:
        raise HTTPException(status_code=403, detail="Not authorized for this owner")

    # Single-file scope
    allowed_files = link.get("allowed_file_ids") or []
    if allowed_files:
        if str(file_meta["_id"]) not in allowed_files:
            raise HTTPException(status_code=403, detail="File not allowed by this link")
        return

    # Category scope
    allowed_categories = link.get("allowed_categories") or []
    if allowed_categories:
        file_cats = (file_meta.get("category") or [])
        if not any(c in allowed_categories for c in file_cats):
            raise HTTPException(status_code=403, detail="File not in shared categories")

def _read_csv_bytes(file_bytes: bytes, encoding_try=("utf-8-sig", "utf-8", "latin-1")) -> list[dict]:
    text = None
    last_err = None
    for enc in encoding_try:
        try:
            text = file_bytes.decode(enc)
            break
        except Exception as e:
            last_err = e
    if text is None:
        raise ValueError(f"Could not decode CSV: {last_err}")

    # Try to sniff delimiter; fallback to comma
    try:
        sample = text[:4096]
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample)
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    # Normalize headers: strip BOM/spaces
    sio = io.StringIO(text)
    reader = csv.reader(sio, delimiter=delimiter)
    try:
        raw_headers = next(reader)
    except StopIteration:
        return []

    headers = [h.replace("\ufeff", "").strip() if h else "" for h in raw_headers]

    rows: list[dict] = []
    for row in reader:
        # Pad shorter rows
        if len(row) < len(headers):
            row += [""] * (len(headers) - len(row))
        rec = {headers[i]: row[i] for i in range(len(headers))}
        rows.append(rec)

    return rows
    

def csv_header_warnings(rows: list[dict], categories: set[str]) -> List[str]:
    """Soft header checks → return warnings (do not block upload)."""
    warns: List[str] = []
    if not rows:
        warns.append("CSV has no rows.")
        return warns
    headers = set(_key(h) for h in rows[0].keys() if h)

    if "equipment" in categories:
        expected_any = {"category", "brand", "type", "size", "notes"}
        if headers.isdisjoint(expected_any):
            warns.append("Equipment CSV doesn't contain common columns like category/brand/type/size/notes.")

    if "performance" in categories:
        perf_any = {"bench", "squat", "vertical", "forty_dash", "40yd", "40_time", "deadlift", "power_clean"}
        if headers.isdisjoint(perf_any):
            warns.append("Performance CSV doesn't contain common columns like bench/squat/vertical/40yd/etc.")

    if "medical" in categories:
        med_any = {"name", "dob", "allergies", "blood_type", "injury_history", "cleared"}
        if headers.isdisjoint(med_any):
            warns.append("Medical CSV doesn't contain common columns like name/dob/allergies/cleared/etc.")
    return warns


# ----------------- CSV ingestors -----------------
def ingest_medical_csv(username: str, rows: list[dict]) -> dict:
    def pick_from_row(row: dict, aliases: list[str]) -> Optional[str]:
        for a in aliases:
            ka = _key(a)
            for col in row.keys():
                kc = _key(col)
                if kc == ka or ka in kc:
                    val = row[col]
                    if _norm(val) != "":
                        return val
        return None

    def pick_from_map(kv: dict, aliases: list[str]) -> Optional[str]:
        for a in aliases:
            ka = _key(a)
            # exact match first
            if ka in kv and _norm(kv[ka]) != "":
                return kv[ka]
            # fuzzy: alias contained in key name
            for k in kv.keys():
                if ka in k and _norm(kv[k]) != "":
                    return kv[k]
        return None

    if not rows:
        log_activity(username, "ingest_medical_csv_empty", {"reason": "no_rows"})
        return {"updated_fields": []}

    # Detect KV shape like headers ["field","value"] (or similar)
    headers = [h for h in rows[0].keys()]
    is_kv = len(headers) == 2 and _key(headers[0]) in {"field","key","name"} and _key(headers[1]) in {"value","val"}

    # Build a normalized key->value map if KV
    kv_map: dict[str,str] = {}
    if is_kv:
        for r in rows:
            k = _key(r.get(headers[0]))
            v = r.get(headers[1])
            if k is not None and _norm(k) != "":
                kv_map[k] = str(v) if v is not None else ""
        log_activity(username, "ingest_medical_csv_detected_kv", {"keys": sorted(list(kv_map.keys()))})
    else:
        log_activity(username, "ingest_medical_csv_headers", {"headers": sorted(headers)})

    # Aliases we’ll accept
    aliases = {
        "name": ["name", "full_name", "athlete_name", "first_last", "athlete"],
        "first": ["first_name", "first"],
        "last": ["last_name", "last"],
        "dob": ["dob", "date_of_birth", "birthdate"],
        "allergies": ["allergies", "allergy"],
        "blood_type": ["blood_type", "blood"],
        "height_in": ["height_in", "height_inches", "height (in)", "height_(in)", "height"],
        "weight_lb": ["weight_lb", "weight_lbs", "weight (lbs)", "weight_(lbs)", "weight"],
        "injury_history": ["injury_history", "injuries", "injury_notes", "injury_note"],
        "cleared": ["cleared", "medically_cleared", "cleared_for_play", "cleared_to_play", "clearance"],
    }

    final_doc = {
        "username": username,
        "updated_at": _utcnow(),
        "raw_rows": rows,  # keep for audit/debug
    }

    def grab(field: str) -> Optional[str]:
        als = aliases[field]
        if is_kv:
            return pick_from_map(kv_map, als)
        # wide rows: check each row until we find a value
        for r in rows:
            v = pick_from_row(r, als)
            if v is not None:
                return v
        return None

    # Name (supports single "name" or first/last)
    name = grab("name")
    if not name:
        first = grab("first")
        last = grab("last")
        name = " ".join(filter(None, [_norm(first) if first else None, _norm(last) if last else None])).strip()
    if name:
        final_doc["name"] = name

    dob = grab("dob")
    if dob:
        final_doc["dob"] = _norm(dob)

    allergies = grab("allergies")
    if allergies:
        final_doc["allergies"] = _norm(allergies)

    blood = grab("blood_type")
    if blood:
        final_doc["blood_type"] = _norm(blood)

    height = grab("height_in")
    if height:
        try:
            final_doc["height_in"] = float(str(height).split()[0])
        except Exception:
            pass

    weight = grab("weight_lb")
    if weight:
        try:
            final_doc["weight_lb"] = float(str(weight).split()[0])
        except Exception:
            pass

    injury = grab("injury_history")
    if injury:
        final_doc["injury_history"] = _norm(injury)

    cleared = _clean_text(grab("cleared"))
    if cleared:
        v = cleared.lower()
        if v in {"yes","y","true","t","1"}: final_doc["cleared"] = True
        elif v in {"no","n","false","f","0"}: final_doc["cleared"] = False

    to_set = {k: v for k, v in final_doc.items() if v is not None}
    medical_history.update_one({"username": username}, {"$set": to_set}, upsert=True)
    log_activity(username, "ingest_medical_csv_result", {"set_keys": sorted(to_set.keys())})
    return {"updated_fields": list(to_set.keys())}


def ingest_equipment_csv(username: str, rows: list[dict]) -> dict:
    items = []
    for row in rows:
        cat = _norm(row.get("category") or row.get("item") or row.get("equipment") or row.get("equipment_type"))
        brand = _norm(row.get("brand"))
        typ = _norm(row.get("type") or row.get("model"))
        size = _norm(row.get("size"))
        notes = _norm(row.get("notes"))
        if cat or brand or typ or size or notes:
            items.append({
                "category": cat or "unspecified",
                "brand": brand,
                "type": typ,
                "size": size,
                "notes": notes,
            })
    doc = {"username": username, "items": items, "updated_at": _utcnow()}
    equipment_col.update_one({"username": username}, {"$set": doc}, upsert=True)
    return {"item_count": len(items)}

def ingest_performance_csv(username: str, rows: list[dict]) -> dict:
    wr_doc = weightroom_col.find_one({"username": username}) or {"username": username}
    updated = {}

    metric_aliases = {
        "bench":        ["bench", "bench_press", "bench_lb", "bench_lbs"],
        "squat":        ["squat", "back_squat", "squat_lb", "squat_lbs"],
        "deadlift":     ["deadlift", "dead_lift", "deadlift_lb", "deadlift_lbs"],
        "power_clean":  ["power_clean", "clean", "pc", "powerclean"],
        "vertical":     ["vertical", "vertical_jump", "vert", "vertical_in", "vertical_inches"],
        "forty_dash":   ["forty", "forty_time", "40yd", "40_yard", "40", "40_time", "40-yard", "40-yard_dash"],
        "shuttle":      ["shuttle", "pro_agility", "shuttle_time", "5-10-5"],
        "broad_jump":   ["broad_jump", "standing_broad", "broad", "broad_inches"],
    }

    def find_metric(row: dict, metric: str, aliases: list[str]) -> Optional[float]:
        for a in aliases:
            k = _key(a)
            for col in row.keys():
                if _key(col) == k or k in _key(col):
                    raw = row[col]
                    # vertical & broad_jump often recorded as feet/inches
                    if metric in {"vertical", "broad_jump"}:
                        return _parse_inches(raw)
                    # times/weights can include units (s, lbs, etc.)
                    return _safe_float_loose(raw)
        return None

    for row in rows:
        for metric, aliases in metric_aliases.items():
            val = find_metric(row, metric, aliases)
            if val is not None:
                wr_doc[metric] = val
                updated[metric] = val

        # Optional: training log notes in the same CSV
        inj = row.get("injury") or row.get("injury_note") or row.get("injury_status")
        det = row.get("details") or row.get("note") or row.get("notes")
        if _norm(inj) or _norm(det):
            training_col.insert_one({
                "username": username,
                "injury": _norm(inj),
                "details": _norm(det),
                "created_at": _utcnow()
            })
            log_activity(
                user_id=username,
                action="add_training_log",
                metadata={"injury": _norm(inj), "details": _norm(det)}
            )

    wr_doc["updated_at"] = _utcnow()
    weightroom_col.update_one({"username": username}, {"$set": wr_doc}, upsert=True)
    log_activity(username, "ingest_performance_csv_result", {"updated": sorted(updated.keys())})
    return {"weightroom_updated": list(updated.keys())}



# ----------------- OCR text parsing (best-effort) -----------------
def extract_structured_from_text(text: str, categories: set[str]) -> dict:
    """
    Extremely light regex-based extraction. Safe to run on OCR text.
    Returns: {"medical": {...}, "equipment_items": [...], "performance": {...}}
    Only fills what it finds.
    """
    out = {}

    # Equipment guesses
    if "equipment" in categories:
        items = []
        # Greedy heuristics: "Cleats: Nike Phantom, Size 11"
        for line in text.splitlines():
            l = line.strip()
            if not l:
                continue
            m = re.match(r"(cleats|helmet|shoulder pads|gloves|mouthpiece)\s*:\s*(.*)", l, re.I)
            if m:
                cat = m.group(1).lower()
                rest = m.group(2)
                brand = None
                size = None
                # brand-ish words
                b = re.search(r"(nike|adidas|riddell|schutt|under armour|ua)\b", rest, re.I)
                if b: brand = b.group(0)
                s = re.search(r"(?:size[:\s]*)(\w+)", rest, re.I)
                if s: size = s.group(1)
                items.append({"category": cat, "brand": brand or "", "type": "", "size": size or "", "notes": "auto-extracted"})
        if items:
            out["equipment_items"] = items

    # Performance guesses
    if "performance" in categories:
        perf = {}
        forty = re.search(r"(?:40[\s\-]*(?:y(?:ard)?(?:\s*dash)?)?)[^\d]*(\d\.\d{1,2})", text, re.I)
        if forty: perf["forty_dash"] = _safe_float(forty.group(1))
        bench = re.search(r"bench[^\d]*(\d{2,4})", text, re.I)
        if bench: perf["bench"] = _safe_float(bench.group(1))
        squat = re.search(r"squat[^\d]*(\d{2,4})", text, re.I)
        if squat: perf["squat"] = _safe_float(squat.group(1))
        vert = re.search(r"(?:vertical|vert)[^\d]*(\d{1,3})", text, re.I)
        if vert: perf["vertical"] = _safe_float(vert.group(1))
        if perf:
            out["performance"] = perf

    # Medical (very light)
    if "medical" in categories:
        med = {}
        allergies = re.search(r"allerg(?:y|ies)\s*:\s*([^\n\r,]+)", text, re.I)
        if allergies: med["allergies"] = _norm(allergies.group(1))
        cleared = re.search(r"(medically\s*cleared|cleared\s*for\s*play)\s*:\s*(yes|no|true|false)", text, re.I)
        if cleared: med["cleared"] = _guess_bool(cleared.group(2))
        if med:
            out["medical"] = med

    return out


# ----------------- Routes -----------------
@router.get("/", response_class=HTMLResponse)
async def upload_page(request: Request, current_user: dict = Depends(get_current_user)):
    files = list(uploads_collection.find({"username": current_user["username"]}).sort("upload_date", -1))
    user_flag = upload_flags.find_one({"username": current_user["username"]}) or {"first_time": True}
    # support showing ?err/ ?msg in the template
    return templates.TemplateResponse("upload_record.html", {
        "request": request,
        "uploaded_files": files,
        "first_time": user_flag["first_time"],
        "err": request.query_params.get("err"),
        "msg": request.query_params.get("msg"),
    })


@router.post("/record")
async def upload_record(
    file: UploadFile = File(...),
    category: List[str] = Form(...),
    current_user: dict = Depends(get_current_user),
):
    username = current_user["username"]
    filename = os.path.basename(file.filename)
    content = await file.read()
    ext = _ext(filename)
    cat_set = {c.lower() for c in (category or [])}

    # 1) Basic validations
    errs = validate_upload(filename, len(content), list(cat_set))  # <-- fixed name & args
    if errs:
        log_activity(username, "upload_validation_failed", {"filename": filename, "errors": errs})
        return RedirectResponse(f"/upload?err={errs[0]}", status_code=303)

    # 2) Save file
    path = os.path.join(UPLOAD_FOLDER, filename)
    with open(path, "wb") as buffer:
        buffer.write(content)

    # 3) Record upload row
    uploads_collection.insert_one({
        "username": username,
        "filename": filename,
        "category": list(cat_set),
        "upload_date": _utcnow(),
    })
    upload_flags.update_one({"username": username}, {"$set": {"first_time": False}}, upsert=True)

    # 4) Smart ingestion
    msg = "File uploaded."
    try:
        if ext == ".csv":
            rows = _read_csv_bytes(content)
            # Optional: soft warnings (not blocking)
            warns = csv_header_warnings(rows, cat_set)
            if warns:
                log_activity(username, "csv_header_warning", {"filename": filename, "warnings": warns})

            if "medical" in cat_set:
                res = ingest_medical_csv(username, rows)
                log_activity(username, "ingest_medical_csv", {"filename": filename, **res})
                msg = "Medical data ingested."
            if "equipment" in cat_set:
                res = ingest_equipment_csv(username, rows)
                log_activity(username, "ingest_equipment_csv", {"filename": filename, **res})
                msg = "Equipment data ingested."
            if "performance" in cat_set:
                res = ingest_performance_csv(username, rows)
                log_activity(username, "ingest_performance_csv", {"filename": filename, **res})
                msg = "Performance data ingested."

        elif ext == ".txt":
            text = content.decode(errors="ignore")
            extracted = extract_structured_from_text(text, cat_set)
            ingested_any = False

            if "medical" in cat_set and extracted.get("medical"):
                medical_history.update_one(
                    {"username": username},
                    {"$set": {**extracted["medical"], "username": username, "updated_at": _utcnow()}},
                    upsert=True,
                )
                log_activity(username, "ingest_medical_text", {"filename": filename})
                ingested_any = True

            if "equipment" in cat_set and extracted.get("equipment_items"):
                equipment_col.update_one(
                    {"username": username},
                    {"$set": {"username": username, "items": extracted["equipment_items"], "updated_at": _utcnow()}},
                    upsert=True,
                )
                log_activity(username, "ingest_equipment_text", {"filename": filename, "count": len(extracted["equipment_items"])})
                ingested_any = True

            if "performance" in cat_set and extracted.get("performance"):
                weightroom_col.update_one(
                    {"username": username},
                    {"$set": {**extracted["performance"], "username": username, "updated_at": _utcnow()}},
                    upsert=True,
                )
                log_activity(username, "ingest_performance_text", {"filename": filename})
                ingested_any = True

            msg = "Data ingested from text." if ingested_any else "Uploaded; no structured data detected."

        elif ext == ".pdf":
            text = extract_text_from_pdf_or_ocr(path)
            extracted = extract_structured_from_text(text, cat_set)
            ingested_any = False

            if "medical" in cat_set and extracted.get("medical"):
                medical_history.update_one(
                    {"username": username},
                    {"$set": {**extracted["medical"], "username": username, "updated_at": _utcnow()}},
                    upsert=True,
                )
                log_activity(username, "ingest_medical_pdf", {"filename": filename})
                ingested_any = True

            if "equipment" in cat_set and extracted.get("equipment_items"):
                equipment_col.update_one(
                    {"username": username},
                    {"$set": {"username": username, "items": extracted["equipment_items"], "updated_at": _utcnow()}},
                    upsert=True,
                )
                log_activity(username, "ingest_equipment_pdf", {"filename": filename, "count": len(extracted["equipment_items"])})
                ingested_any = True

            if "performance" in cat_set and extracted.get("performance"):
                weightroom_col.update_one(
                    {"username": username},
                    {"$set": {**extracted["performance"], "username": username, "updated_at": _utcnow()}},
                    upsert=True,
                )
                log_activity(username, "ingest_performance_pdf", {"filename": filename})
                ingested_any = True

            msg = "Data ingested from PDF." if ingested_any else "Uploaded; no structured data detected."

        elif ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            text = ocr_image_path(path)
            extracted = extract_structured_from_text(text, cat_set)
            ingested_any = False

            if "equipment" in cat_set and extracted.get("equipment_items"):
                equipment_col.update_one(
                    {"username": username},
                    {"$set": {"username": username, "items": extracted["equipment_items"], "updated_at": _utcnow()}},
                    upsert=True,
                )
                log_activity(username, "ingest_equipment_image", {"filename": filename, "count": len(extracted["equipment_items"])})
                ingested_any = True

            if "performance" in cat_set and extracted.get("performance"):
                weightroom_col.update_one(
                    {"username": username},
                    {"$set": {**extracted["performance"], "username": username, "updated_at": _utcnow()}},
                    upsert=True,
                )
                log_activity(username, "ingest_performance_image", {"filename": filename})
                ingested_any = True

            if "medical" in cat_set and extracted.get("medical"):
                medical_history.update_one(
                    {"username": username},
                    {"$set": {**extracted["medical"], "username": username, "updated_at": _utcnow()}},
                    upsert=True,
                )
                log_activity(username, "ingest_medical_image", {"filename": filename})
                ingested_any = True

            msg = "Data ingested from image." if ingested_any else "Uploaded; no structured data detected."

    except ValueError as e:
        log_activity(username, "csv_parse_error", {"filename": filename, "error": str(e)})
        return RedirectResponse(f"/upload?err=CSV parse error: {str(e)}", status_code=303)
    except Exception as e:
        log_activity(username, "ingest_error", {"filename": filename, "error": str(e)})
        return RedirectResponse(f"/upload?err=Could not ingest: {str(e)}", status_code=303)

    # 5) Base upload activity
    log_activity(username, "upload_file", {"filename": filename, "category": list(cat_set)})
    return RedirectResponse(f"/upload?msg={msg}", status_code=303)


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    token: str | None = Query(None),
    email: str | None = Query(None),
    current_user: dict | None = Depends(get_current_user_optional),
):
    # Validate object id
    try:
        oid = ObjectId(file_id)
    except (InvalidId, TypeError):
        return JSONResponse({"error": "Invalid file id"}, status_code=400)

    file_meta = uploads_collection.find_one({"_id": oid})
    if not file_meta:
        return JSONResponse({"error": "File not found"}, status_code=404)

    # 1) If the owner is logged in, allow direct download
    if current_user and current_user.get("username") == file_meta["username"]:
        filepath = os.path.join(UPLOAD_FOLDER, file_meta["filename"])
        return FileResponse(filepath, filename=file_meta["filename"])

    # 2) Otherwise require a valid share token + email (single-file or category-scoped)
    try:
        validate_shared_download(file_meta, token, email)
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)

    filepath = os.path.join(UPLOAD_FOLDER, file_meta["filename"])
    return FileResponse(filepath, filename=file_meta["filename"])


