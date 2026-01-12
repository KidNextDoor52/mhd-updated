import pandas as pd
import hashlib


PII_COLUMNS = {"name", "email", "phone", "address", "ssn"}

def hash_value(v: str) -> str:
    return hashlib.sha256(str(v).encode("utf-8")).hexdigest()

def deidentify(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    #drop direct identifiers
    for c in PII_COLUMNS & set(df.columns):
        df.drop(columns=[c], inplace=True)

    #example: coarse=grain location/age if present
    if "zip" in df.columns:
        df["zip3"] = df["zip"].astype(str).str[:3]
        df.drop(columns=["zip"], inplace=True)
    
    if "age" in df.columns:
        df["age_band"] = pd.cut(df["age"], bins=[0,18,30,45,60,120], labels=["<18","18-29","30-44","45-59","60+"])
        # keep raw age only if necessary; else drop
        # df.drop(columns=["age"], inplace=True)
    return df
