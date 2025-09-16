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
    return (s or "").strip().lower().replace(" ", "_").replace("-", "_")

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

def _read_csv_bytes(file_bytes: bytes, encoding_try=("utf-8", "latin-1")) -> list[dict]:
    for enc in encoding_try:
        try:
            text = file_bytes.decode(enc)
            reader = csv.DictReader(io.StringIO(text))
            if reader.fieldnames is None:
                continue
            return [dict(r) for r in reader]
        except Exception:
            continue
    raise ValueError("Could not parse CSV with common encodings (utf-8, latin-1).")

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
    scalar_map = {
        "name": {"aliases": ["name", "full_name", "athlete_name"]},
        "dob": {"aliases": ["dob", "date_of_birth"]},
        "allergies": {"aliases": ["allergies"]},
        "blood_type": {"aliases": ["blood_type", "blood"]},
        "height": {"aliases": ["height", "height_in", "height_inches"]},
        "weight": {"aliases": ["weight", "weight_lb", "weight_lbs"]},
        "injury_history": {"aliases": ["injury_history", "injuries"]},
        "cleared": {"aliases": ["cleared", "medically_cleared", "cleared_for_play"]},
    }
    final_doc = {
        "username": username,
        "updated_at": _utcnow(),
        "raw_rows": rows,
    }

    def find_val(row: dict, aliases: list[str]) -> Optional[str]:
        for a in aliases:
            k = _key(a)
            for col in row.keys():
                if _key(col) == k or k in _key(col):
                    return row[col]
        return None

    for row in rows:
        for field, spec in scalar_map.items():
            val = find_val(row, spec["aliases"])
            if val is not None and _norm(val) != "":
                if field == "height":
                    final_doc["height_in"] = _safe_float(val)
                elif field == "weight":
                    final_doc["weight_lb"] = _safe_float(val)
                elif field == "cleared":
                    final_doc["cleared"] = _guess_bool(val)
                else:
                    final_doc[field] = val

    medical_history.update_one({"username": username}, {"$set": final_doc}, upsert=True)
    return {"updated_fields": list(final_doc.keys())}

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
        "bench": ["bench", "bench_press", "bench_lb", "bench_lbs"],
        "squat": ["squat", "back_squat", "squat_lb", "squat_lbs"],
        "deadlift": ["deadlift", "dead_lift", "deadlift_lb", "deadlift_lbs"],
        "power_clean": ["power_clean", "clean", "pc", "powerclean"],
        "vertical": ["vertical", "vertical_jump", "vert", "vertical_in", "vertical_inches"],
        "forty_dash": ["forty", "forty_time", "40yd", "40_yard", "40", "40_time", "40-yard", "40-yard_dash"],
        "shuttle": ["shuttle", "pro_agility", "shuttle_time", "5-10-5"],
        "broad_jump": ["broad_jump", "standing_broad", "broad", "broad_inches"],
    }
    def find_metric(row: dict, aliases: list[str]) -> Optional[float]:
        for a in aliases:
            k = _key(a)
            for col in row.keys():
                if _key(col) == k or k in _key(col):
                    return _safe_float(row[col])
        return None

    for row in rows:
        for metric, aliases in metric_aliases.items():
            val = find_metric(row, aliases)
            if val is not None:
                wr_doc[metric] = val
                updated[metric] = val
        inj = row.get("injury") or row.get("injury_note") or row.get("injury_status")
        det = row.get("details") or row.get("note") or row.get("notes")
        if _norm(inj) or _norm(det):
            training_col.insert_one({"username": username, "injury": _norm(inj), "details": _norm(det), "created_at": _utcnow()})
            log_activity(user_id=username, action="add_training_log", metadata={"injury": _norm(inj), "details": _norm(det)})

    wr_doc["updated_at"] = _utcnow()
    weightroom_col.update_one({"username": username}, {"$set": wr_doc}, upsert=True)
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


