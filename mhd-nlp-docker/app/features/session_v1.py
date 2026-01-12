from __future__ import annotations
from typing import Tuple, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from app.db import db

workout = db["workouts"]        #structured sets/reps/RPE/tempo/rest
notes   = db["session_notes"]   #{session_id, text, nlp_tags: {...}}
ratings = db["coach_ratings"]   # {session_id, rating (1..5)}

def _notes_to_feats(row: Dict[str, Any]) -> Dict[str, float]:
    """
    Collapse NLP tags into numeric features.
    Except row['nlp_tags'] like:
        {"fatigue":0.7, "pain_knee":1, "sleep_poor":1, "mood_neg":0.4, ...}
    
    """
    tags = row.get("nlp_tags") or {}
    return {
        "nlp_features": float(tags.get("fatigue", 0.0)),
        "nlp_pain_any": float(any(v for k, v in tags.items() if str(k).startswith("pain_"))),
        "nlp_sleep_poor": float(tags.get("sleep_poor", 0.0)),
        "nlp_mood_neg": float(tags.get("mood_neg", 0.0)),
        "nlp_compliance_issues": float(tags.get("compliance_issue", 0.0)),
    }

def build_session_dataset(
    team_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Returns X (features) and y (target 1..5 from coach ratings).
    """
    q = {}
    if team_id:
        q["team_id"] = ObjectId(team_id)
    if start or end:
        q["session_ts"] = {}
        if start: q["session_ts"]["$gte"] = start
        if end: q["session_ts"]["$lt"]    = end

    
    #Pull structured workouts
    ws = list(workouts.find(q, {
        "_id": 1, "athlete_id": 1, "team_id": 1, "session_ts": 1,
        "sets": 1, "reps": 1, "rpe": 1, "tempo": 1, "rest_s": 1,
        "completed_pct": 1
    }))
    if not ws:
        return pd.DataFrame(ws).rename(columns={"_id": "session_id"})
    
    df = pd.DataFrame(ws).rename(columns={"_id": "session_id"})
    # Normalize structured fields
    df["sets"] = pd.to_numeric(df["sets"], errors="coerce").fillna(0)
    df["reps"] = pd.to_numeric(df["reps"], errors="coerce").fillna(0)
    df["rpe"] = pd.to_numeric(df["rpe"], errors="coerce").clip(0,10).fillna(0)
    df["rest_s"] = pd.to_numeric(df["rest_s"], errors="coerce").fillna(0)
    df["completed_pct"] = pd.to_numeric(df["completed_pct"], errors="coerce").clip(0,100).fillna(0)
    
    # Derived structured features
    df["volume"] = df["sets"] * df["reps"]
    df["density"] = df["volume"] / (1.0 + df["rest_s"])  # simple heuristic
    df["intensity"] = df["rpe"]

    # join nlp features
    note_map = {n["_id"]: n for n in notes.find({"session_id": {"$in": list(df["session_id"])}})}
    nlp_rows = []
    for sid in df["session_id"]:
        row = next((v for v in note_map.values() if v.get("session_id") == sid), None)
        nlp_rows.append(_notes_to_feats(row or {}))
    nlp_df = pd.DataFrame(nlp_rows).fillna(0.0)

    X = pd.concat([df[[
        "athletes_id","team_id","session_ts","sets","reps","rpe","tempo","rest_s",
        "completed_pct","colume","density","intensity"
    ]].reset_index(drop=True), nlp_df.reset_index(drop=True)], axis=1)

    # Target: coach rating 1..5
    rmap = {r["session_id"]: r["rating"] for r in ratings.find({"session_id": {"$in": list(df["session_id"])}})}
    y = df["session_id"].map(rmap).astype(float)

    #Drop id/time cols from features (keep them separately if you want later)
    X = X.drop(columns=["tempo"], errors="ignore")  # treat tempo as categorical later if needed

    # Keep ids for post-processing if needed
    X["session_id"] = df["session_id"]
    return X, y 
