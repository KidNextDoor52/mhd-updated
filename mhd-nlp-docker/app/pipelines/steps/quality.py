import pandas as pd
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any

REQUIRED = ["age", "bp", "hr", "target"]

def basic_schema_check(df: pd.DataFrame) -> dict:
    ok, issues = True, []
    for c in REQUIRED:
        if c not in df.columns:
            ok = False; issues.append(f"missing column: {c}")
    if "age" in df and ((df["age"] < 0) | (df["age"] > 120)).any():
        ok = False; issues.append("age out of plausible bounds")
    return {"ok": ok, "issues": issues}

class SessionRow(BaseModel):
    sets: float = Field(ge=0)
    reps: float = Field(ge=0)
    rpe:  float = Field(ge=0, le=10)
    completed_pct: float = Field(ge=0, le=100)
    volume: float = Field(ge=0)
    density: float = Field(ge=0)
    intensity: float = Field(ge=0, le=10)
    nlp_fatigue: float = Field(ge=0)
    nlp_pain_any: float = Field(ge=0)
    nlp_sleep_poor: float = Field(ge=0)
    nlp_mood_neg: float = Field(ge=0)
    nlp_compliance_issues: float = Field(ge=0)

def session_schema_check(df) -> Dict[str, Any]:
    issues: List[str] = []
    sample = df[[
        "sets","reps","rpe","completed_pct","volume","density","intensity",
        "nlp_fatigue","nlp_pain_any","nlp_sleep_poor","nlp_mood_neg","nlp_compliance_issiues"
    ]].head(100).to_dict(orient="records")
    for i, row in enumerate(sample):
        try:
            SessionRow(**row)
        except ValidationError as e:
            issues.append(f"row {i}: {e.errors()!r}")
            if len(issues) > 10:
                break
    return {"ok": not issues, "issues": issues}