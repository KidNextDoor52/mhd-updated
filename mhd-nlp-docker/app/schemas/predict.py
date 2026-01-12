from pydantic import BaseModel, Field
from typing import List

class RiskItem(BaseModel):
    age: float = Field(ge=10, le=100)
    bp: float
    hr: float

class RiskRequest(BaseModel):
    items: List[RiskItem]

class SessionItem(BaseModel):
    sets: float = Field(ge=0)
    reps: float = Field(ge=0)
    rpe:  float = Field(ge=0)
    rest_s: float = Field(ge=0)
    completed_pct: float = Field(ge=0, le=100)
    nlp_fatigue: float = 0
    nlp_pain_any: float = 0
    nlp_sleep_poor: float = 0
    nlp_mood_neg: float = 0
    nlp_compliance_issues: float = 0

class SessionScoreRequest(BaseModel):
    items: List[SessionItem]

    