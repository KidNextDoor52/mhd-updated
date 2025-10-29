import os, uuid
import pandas as pd, numpy as np
import mlflow

from .steps.train import train_basic
from .steps.validate import validate_metrics
from .steps.deploy import promote

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))

def run_training_job():
    job_id = str(uuid.uuid4())

    # synthetic dataset (replace with real ingest late)
    x = pd.DataFrame({
        "age": np.random.randint(18, 80, 500),
        "bp":  np.random.normal(120, 15, 500),
        "hr":  np.random.normal(72, 10, 500),
    })
    y = ((x["age"] > 50) & (x["bp"] > 130)).astype(int)
    df = x.copy(); df["target"] = y



    metrics = train_basic(df)
    if validate_metrics(metrics):
        promote({"job_id": job_id, "metrics": metrics})
    return job_id

if __name__ == "__main__":
    print(run_training_job)