import pandas as pd
from io import BytesIO

def csv_bytes_to_df(b: bytes) -> pd.DataFrame:
    return pd.read_csv(BytesIO(b))
