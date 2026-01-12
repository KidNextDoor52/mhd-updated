def load_latest_model_for(registered_model_name: str):
    client = MlflowClient()
    try:
        vers = client.get_latest_versions(registered_model_name, stages=["Production"])
        if vers:
            v = vers[0]
            model_uri = f"models:/{registered_model_name}/{v.version}"
            model = mlflow.pyfunc.load_model(model_uri)
            return model, {"run_id": v.run_id, "model_version": v.version, "source":"registry"}
    except Exception:
        pass
    # fallback: last run tagged with use_case
    exp = client.get_experiment_by_name(os.getenv("MODEL_NAME","mhd_logreg")) or client.create_experiment(os.getenv("MODEL_NAME","mhd_logreg"))
    runs = client.search_runs(exp.experiment_id, "tags.`mlflow.runName` LIKE '%injury_risk%'", order_by=["attributes.start_time DESC"], max_results=1)
    if not runs: raise RuntimeError("No runs found for model")
    run = runs[0]; model = mlflow.pyfunc.load_model(f"runs:/{run.info.run_id}/model")
    return model, {"run_id": run.info.run_id, "model_version": None, "source":"runs"}