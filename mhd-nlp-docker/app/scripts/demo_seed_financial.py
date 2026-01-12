# app/demo_seed_financial.py

from datetime import datetime, timedelta, timezone

from app.db import db, users

fin_clients = db["financial_clients"]
fin_alerts = db["financial_alerts"]
fin_kyc = db["financial_kyc"]


def seed_financial_demo():
    now = datetime.now(timezone.utc)
    org_id = "org_fin_001"

    # --- Ensure demo_fin_1 user exists and is wired to this org/vertical ---
    users.update_one(
        {"username": "demo_fin_1"},
        {
            "$set": {
                "username": "demo_fin_1",
                "email": "demo_fin_1@mhd.local",
                "role": "org_user",
                "vertical": "financial",
                "org_id": org_id,
                "demo": True,
            }
        },
        upsert=True,
    )

    # Clear old demo data for this org so you can re-run the script
    fin_clients.delete_many({"demo": True, "org_id": org_id})
    fin_alerts.delete_many({"demo": True, "org_id": org_id})
    fin_kyc.delete_many({"demo": True, "org_id": org_id})

    # --- Clients portfolio (10 total) ---
    clients = [
        ("CL-1001", "Atlas Holdings", "active", "Institutional"),
        ("CL-1002", "Horizon Ventures", "active", "Wealth"),
        ("CL-1003", "Northbridge Capital", "onboarding", "Institutional"),
        ("CL-1004", "Silverline Asset Mgmt", "active", "Wealth"),
        ("CL-1005", "Cedar Ridge Family Office", "onboarding", "Wealth"),
        ("CL-1006", "Mariner Global", "active", "Institutional"),
        ("CL-1007", "BluePeak Advisors", "active", "Wealth"),
        ("CL-1008", "Everstone Partners", "onboarding", "Institutional"),
        ("CL-1009", "Summit Ridge Fund", "active", "Institutional"),
        ("CL-1010", "Lighthouse Capital", "active", "Wealth"),
    ]

    fin_clients.insert_many(
        [
            {
                "demo": True,
                "org_id": org_id,
                "client_id": cid,
                "name": name,
                "status": status,      # "active" or "onboarding"
                "segment": segment,
            }
            for (cid, name, status, segment) in clients
        ]
    )

    # --- High-risk accounts / alerts (10 rows) ---
    alerts = [
        ("ACC-9001", "Atlas Holdings", 0.87, "review", "Large cash deposits", 1),
        ("ACC-9002", "Horizon Ventures", 0.76, "open", "Unusual jurisdiction pattern", 2),
        ("ACC-9003", "Northbridge Capital", 0.81, "review", "Rapid beneficiary changes", 3),
        ("ACC-9004", "Silverline Asset Mgmt", 0.65, "monitoring", "Structuring behaviour", 5),
        ("ACC-9005", "Cedar Ridge Family Office", 0.92, "open", "PEP match + high volume", 0),
        ("ACC-9006", "Mariner Global", 0.71, "review", "Multiple wire destinations", 6),
        ("ACC-9007", "BluePeak Advisors", 0.55, "monitoring", "Dormant account reactivation", 9),
        ("ACC-9008", "Everstone Partners", 0.83, "open", "High-risk country exposure", 4),
        ("ACC-9009", "Summit Ridge Fund", 0.68, "review", "Adverse news hit", 7),
        ("ACC-9010", "Lighthouse Capital", 0.74, "monitoring", "Unusual cash withdrawals", 8),
    ]

    fin_alerts.insert_many(
        [
            {
                "demo": True,
                "org_id": org_id,
                "account_id": acc,
                "client_name": client,
                "score": score,
                # "open" + "review" should both count into high-risk
                "status": status,
                "rule": rule,
                "ts": (now - timedelta(days=days_ago)).isoformat(),
            }
            for (acc, client, score, status, rule, days_ago) in alerts
        ]
    )

    # --- KYC / AML checks (10 rows) ---
    kyc_rows = [
        ("Atlas Holdings", "KYC refresh", "pending", 3),
        ("Horizon Ventures", "Initial KYC", "overdue", -2),
        ("Northbridge Capital", "AML screening", "pending", 10),
        ("Silverline Asset Mgmt", "Periodic review", "pending", 5),
        ("Cedar Ridge Family Office", "Source of wealth", "overdue", -5),
        ("Mariner Global", "EDD review", "pending", 14),
        ("BluePeak Advisors", "KYC refresh", "pending", 2),
        ("Everstone Partners", "Sanctions rescreen", "pending", 7),
        ("Summit Ridge Fund", "Initial KYC", "overdue", -1),
        ("Lighthouse Capital", "Adverse media review", "pending", 9),
    ]

    fin_kyc.insert_many(
        [
            {
                "demo": True,
                "org_id": org_id,
                "client_name": client,
                "check_type": ctype,
                "status": status,  # pending / overdue
                "due_at": (now + timedelta(days=offset)).date().isoformat(),
            }
            for (client, ctype, status, offset) in kyc_rows
        ]
    )

    print("Seeded financial demo data for org_fin_001 / demo_fin_1")


if __name__ == "__main__":
    seed_financial_demo()
