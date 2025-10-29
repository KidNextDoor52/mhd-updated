import mlflow
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

mlflow.sklearn.autolog()

def train_basic(df, target_col="target"):
    x = df.drop(columns=[target_col])
    y = df[target_col]
    xtr, xte, ytr, yte = train_test_split(x, y, test_size=0.2, random_state=42)
    
    with mlflow.start_run(run_name="logreg"):
        model = LogisticRegression(max_iter=500).fit(xtr, ytr)
        auc =  roc_auc_score(yte, model.predict_proba(xte)[:, 1])
        mlflow.log_metric("val_auc", float(auc))
        mlflow.sklearn.log_model(model, "model")
        return {"val_auc": float(auc)}