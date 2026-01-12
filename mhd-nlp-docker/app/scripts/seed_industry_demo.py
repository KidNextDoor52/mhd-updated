# app/scripts/seed_industry_demo.py

from datetime import datetime, timedelta, timezone
import random

from app.db import db

UTC = timezone.utc

oil_incidents = db["oil_gas_incidents"]
oil_permits = db["oil_gas_permits"]
oil_trainings = db["oil_gas_trainings"]

fin_clients = db["financial_clients"]
fin_alerts = db["financial_alerts"]
fin_kyc = db["financial_kyc"]

law_matters = db["law_matters"]
law_deadlines = db["law_deadlines"]
law_signatures = db["law_signatures"]


def seed_oil_gas():
    print("[seed] oil & gas...")
    oil_incidents.delete_many({"demo": True})
    oil_permits.delete_many({"demo": True})
    oil_trainings.delete_many({"demo": True})

    now = datetime.now(UTC)

    # both generic demo + your org_oil_001
    org_ids = ["org_oil_demo", "org_oil_001"]

    sites = ["West Pad A", "Central Processing", "North Field", "Pad B", "South Tank Farm"]
    types = ["Near miss", "Spill", "TRIR recordable", "Equipment failure", "Unsafe act"]
    severities = ["low", "medium", "high"]
    statuses = ["open", "closed", "investigating", "monitoring"]

    for org in org_ids:
        # --- 10 incidents ---
        incidents = []
        for i in range(10):
            incidents.append(
                {
                    "demo": True,
                    "org_id": org,
                    "ts": now - timedelta(days=random.randint(1, 30)),
                    "site": random.choice(sites),
                    "type": random.choice(types),
                    "severity": random.choice(severities),
                    "status": random.choice(statuses),
                }
            )
        oil_incidents.insert_many(incidents)

        # --- 10 permits ---
        permit_names = [
            "Air Emissions Permit",
            "Drilling Permit – Pad B",
            "Produced Water Disposal",
            "Compressor Operating Permit",
            "Tank Battery VOC Permit",
            "Offshore Platform Permit",
            "Blowout Preventer Cert",
            "Pipeline Integrity Cert",
            "Flare Stack Authorization",
            "H2S Contingency Plan",
        ]
        permits = []
        for i, name in enumerate(permit_names):
            permits.append(
                {
                    "demo": True,
                    "org_id": org,
                    "name": name,
                    "location": random.choice(sites),
                    "owner": random.choice(
                        ["EHS Manager", "Drilling Supervisor", "Ops Superintendent"]
                    ),
                    "expires_at": (now + timedelta(days=10 + i * 5)).date().isoformat(),
                }
            )
        oil_permits.insert_many(permits)

        # --- 10 training rows ---
        trainings = []
        employees = [
            "Alex Johnson",
            "Morgan Lee",
            "Chris Patel",
            "Dana Wright",
            "Jordan Smith",
            "Taylor Brown",
            "Riley Chen",
            "Samir Gupta",
            "Jamie Torres",
            "Casey Nguyen",
        ]
        courses = [
            "H2S Safety",
            "Lockout/Tagout",
            "Confined Space Entry",
            "Hot Work",
            "Fall Protection",
            "Stop Work Authority",
        ]
        for emp in employees:
            trainings.append(
                {
                    "demo": True,
                    "org_id": org,
                    "employee": emp,
                    "role": random.choice(["Field Tech", "Operator", "Supervisor"]),
                    "name": random.choice(courses),
                    "status": random.choice(["on_time", "overdue"]),
                    "due_at": (now + timedelta(days=random.randint(-5, 25)))
                    .date()
                    .isoformat(),
                }
            )
        oil_trainings.insert_many(trainings)

    print("[seed] oil & gas done.")


def seed_financial():
    """
    Generic demo org (org_fin_demo).

    For your more detailed org_fin_001 + demo_fin_1,
    use app/demo_seed_financial.py so the counts
    line up nicely with that dashboard.
    """
    print("[seed] financial (generic demo)...")
    fin_clients.delete_many({"demo": True, "org_id": "org_fin_demo"})
    fin_alerts.delete_many({"demo": True, "org_id": "org_fin_demo"})
    fin_kyc.delete_many({"demo": True, "org_id": "org_fin_demo"})

    now = datetime.now(UTC)
    org = "org_fin_demo"

    client_names = [
        "Atlas Holdings",
        "Horizon Ventures",
        "Northbridge Capital",
        "Silverline Asset Mgmt",
        "Cedar Ridge Family Office",
        "Mariner Global",
        "BluePeak Advisors",
        "Everstone Partners",
        "Summit Ridge Fund",
        "Lighthouse Capital",
    ]

    # 10 clients
    fin_clients.insert_many(
        [
            {
                "demo": True,
                "org_id": org,
                "client_id": f"C-{1001+i}",
                "name": nm,
                "status": random.choice(["active", "onboarding"]),
            }
            for i, nm in enumerate(client_names)
        ]
    )

    # 10 alerts
    fin_alerts.insert_many(
        [
            {
                "demo": True,
                "org_id": org,
                "account_id": f"ACC-9{str(1_000 + i)[1:]}",
                "client_name": random.choice(client_names),
                "score": round(random.uniform(0.4, 0.95), 2),
                "status": random.choice(["open", "review", "monitoring"]),
                "ts": now - timedelta(days=random.randint(0, 10)),
            }
            for i in range(10)
        ]
    )

    # 10 KYC rows
    fin_kyc.insert_many(
        [
            {
                "demo": True,
                "org_id": org,
                "client_name": random.choice(client_names),
                "check_type": random.choice(
                    ["Initial KYC", "KYC refresh", "AML screening", "EDD review"]
                ),
                "status": random.choice(["pending", "overdue"]),
                "due_at": (now + timedelta(days=random.randint(-5, 15)))
                .date()
                .isoformat(),
            }
            for _ in range(10)
        ]
    )

    print("[seed] financial (generic demo) done.")


def seed_law():
    print("[seed] law...")
    law_matters.delete_many({"demo": True})
    law_deadlines.delete_many({"demo": True})
    law_signatures.delete_many({"demo": True})

    now = datetime.now(UTC)

    # both generic demo + your org_law_001
    org_ids = ["org_law_demo", "org_law_001"]

    for org in org_ids:
        # 10 matters
        matters = []
        for i in range(10):
            matters.append(
                {
                    "demo": True,
                    "org_id": org,
                    "name": f"Case {chr(65+i)} v. Contoso Corp",
                    "client": f"Client {chr(65+i)}",
                    "owner": random.choice(["Sarah Bush", "Alex Kim", "Jordan Lee"]),
                    "status": random.choice(["open", "closed"]),
                    "opened_at": (now - timedelta(days=random.randint(5, 60)))
                    .date()
                    .isoformat(),
                }
            )
        law_matters.insert_many(matters)

        matter_names = [m["name"] for m in matters]

        # 10 deadlines
        deadlines = []
        for i in range(10):
            deadlines.append(
                {
                    "demo": True,
                    "org_id": org,
                    "name": random.choice(
                        [
                            "Discovery cutoff",
                            "Pretrial motion",
                            "Expert designation",
                            "Mediation deadline",
                            "Initial disclosures",
                        ]
                    ),
                    "matter_name": random.choice(matter_names),
                    "owner": random.choice(["Sarah Bush", "Alex Kim", "Jordan Lee"]),
                    "due_at": (now + timedelta(days=random.randint(1, 30)))
                    .date()
                    .isoformat(),
                }
            )
        law_deadlines.insert_many(deadlines)

        # 10 signatures
        signatures = []
        for i in range(10):
            signatures.append(
                {
                    "demo": True,
                    "org_id": org,
                    "doc_name": random.choice(
                        [
                            "Settlement Agreement",
                            "Engagement Letter",
                            "Plea Offer",
                            "NDA",
                            "Release of Claims",
                        ]
                    ),
                    "matter_name": random.choice(matter_names),
                    "signer": random.choice(
                        [
                            "Client Representative",
                            "Opposing Counsel",
                            "Court Clerk",
                            "General Counsel",
                        ]
                    ),
                    "status": random.choice(["pending", "overdue", "sent"]),
                    "sent_at": (now - timedelta(days=random.randint(0, 14)))
                    .date()
                    .isoformat(),
                }
            )
        law_signatures.insert_many(signatures)

    print("[seed] law done.")


if __name__ == "__main__":
    seed_oil_gas()
    seed_financial()
    seed_law()
    print("[seed] industry demo complete.")
