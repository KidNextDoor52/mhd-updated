def validate_metrics(metrics: dict) -> bool:
    # basic promotio threshold (tune later)
    return metrics.get("val_auc", 0.0) >= 0.70