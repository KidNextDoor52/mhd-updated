import mlflow
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

# Enable autologging once
mlflow.sklearn.autolog()

def train_basic(df, target_col: str = "target"):
    """
    Generic binary classifier trainer.
    Expects df with a numeric target column (0/1) named `target_col`.
    """
    # Split features / target
    X = df.drop(columns=[target_col])
    y = df[target_col]

    xtr, xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

    # Allow nested runs so we don't clash with any outer runs
    with mlflow.start_run(run_name="logreg", nested=True) as run:
        model = LogisticRegression(max_iter=500).fit(xtr, ytr)
        auc = roc_auc_score(yte, model.predict_proba(xte)[:, 1])

        # Explicit logging (on top of autolog)
        mlflow.log_metric("val_auc", float(auc))
        mlflow.sklearn.log_model(model, "model")

        return {
            "val_auc": float(auc),
            "run_id": run.info.run_id,
            "model_uri": f"runs:/{run.info.run_id}/model",
        }