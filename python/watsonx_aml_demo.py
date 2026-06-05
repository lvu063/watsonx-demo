"""
watsonx_aml_demo.py
-------------------
IBM watsonx Enterprise AI Demo — AML Analytics with AI Insights

Extends the TD Financial Crime Analytics project by integrating watsonx.ai
as an AI layer on top of the existing AML pipeline. Demonstrates the exact
use case IBM is pitching to banks right now: using foundation models to
generate compliance insights from structured transaction data.

IBM context: TD Bank is one of IBM's largest Canadian clients. The $3B AML
overhaul TD is executing is exactly the kind of engagement IBM Consulting
supports. This demo shows how watsonx.ai fits into that workflow.

Usage:
    python python/watsonx_aml_demo.py              # full demo
    python python/watsonx_aml_demo.py --mock       # no API key needed
    python python/watsonx_aml_demo.py --export     # save insights to CSV
"""

from __future__ import annotations
import argparse
import json
import os
import random
from dataclasses import dataclass
from datetime import date, timedelta

try:
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    WATSONX_AVAILABLE = True
except ImportError:
    WATSONX_AVAILABLE = False

IBM_API_KEY    = os.getenv("IBM_API_KEY", "")
IBM_PROJECT_ID = os.getenv("IBM_PROJECT_ID", "")
IBM_URL        = os.getenv("IBM_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_MODEL  = "ibm/granite-13b-instruct-v2"

# ── Synthetic AML data ────────────────────────────────────────────────────────

rng = random.Random(42)

def generate_alert_summary() -> dict:
    """Generate a realistic AML alert summary for watsonx to analyse."""
    return {
        "customer_id": f"C{rng.randint(10000,99999)}",
        "risk_tier": rng.choice(["High", "Critical"]),
        "composite_score": rng.randint(72, 98),
        "flagged_transactions": rng.randint(3, 12),
        "total_flagged_amount": round(rng.uniform(45000, 280000), 2),
        "flag_reasons": rng.sample(
            ["STRUCTURING", "HIGH_RISK_JURISDICTION", "ROUND_AMOUNT_CASH", "HIGH_VELOCITY"],
            k=rng.randint(1, 3)
        ),
        "pep_status": rng.random() < 0.3,
        "high_risk_countries": rng.sample(["Cayman Islands", "Panama", "Nigeria"], k=rng.randint(1,2)),
        "alert_age_days": rng.randint(1, 14),
        "prior_escalations": rng.randint(0, 2),
        "segment": rng.choice(["Commercial", "Wealth", "Small Business"]),
    }


# ── watsonx AI insight generation ─────────────────────────────────────────────

INSIGHT_PROMPT = """You are an AML compliance analyst at a major Canadian bank.
Review the following customer alert summary and provide:
1. A concise risk assessment (2-3 sentences)
2. The primary red flag and its regulatory significance
3. A recommended next action (escalate / enhanced review / close)

Alert Summary:
{summary}

Respond in this format:
RISK ASSESSMENT: [your assessment]
PRIMARY RED FLAG: [flag and regulatory basis]
RECOMMENDED ACTION: [action with brief justification]"""


def generate_watsonx_insight(alert: dict, mock: bool = False) -> str:
    """Use watsonx.ai to generate a compliance insight from alert data."""
    summary = json.dumps(alert, indent=2)
    prompt = INSIGHT_PROMPT.format(summary=summary)

    if mock or not (IBM_API_KEY and IBM_PROJECT_ID and WATSONX_AVAILABLE):
        # Realistic mock insights
        mock_insights = [
            f"RISK ASSESSMENT: Customer {alert['customer_id']} exhibits critical-tier risk with a composite score of {alert['composite_score']}/100, driven by {alert['flagged_transactions']} flagged transactions totalling ${alert['total_flagged_amount']:,.2f}. The combination of {', '.join(alert['flag_reasons'])} across {alert['alert_age_days']} days suggests active layering behaviour.\nPRIMARY RED FLAG: {alert['flag_reasons'][0]} — pattern consistent with PCMLTFA s.9 structuring or high-risk jurisdiction layering per FINTRAC Guidance FIN-2018-G001.\nRECOMMENDED ACTION: ESCALATE to senior investigator. PEP status confirmed; enhanced due diligence required. File STR if investigation confirms reasonable grounds.",
            f"RISK ASSESSMENT: Alert pattern for {alert['customer_id']} shows concentrated exposure to {', '.join(alert['high_risk_countries'])} above FINTRAC risk thresholds. With {alert['prior_escalations']} prior escalations and current score of {alert['composite_score']}, this customer warrants priority review.\nPRIMARY RED FLAG: HIGH_RISK_JURISDICTION — transactions with counterparties in FATF-monitored jurisdictions without clear business purpose.\nRECOMMENDED ACTION: ENHANCED REVIEW — request source of funds documentation, review beneficial ownership, and assess against sanctions lists before proceeding.",
        ]
        return rng.choice(mock_insights)

    credentials = Credentials(url=IBM_URL, api_key=IBM_API_KEY)
    client = APIClient(credentials=credentials, project_id=IBM_PROJECT_ID)
    model = ModelInference(
        model_id=WATSONX_MODEL,
        api_client=client,
        params={
            GenParams.MAX_NEW_TOKENS: 250,
            GenParams.TEMPERATURE: 0.2,
            GenParams.TOP_P: 0.85,
        }
    )
    return model.generate_text(prompt=prompt)


# ── Alert queue analysis ───────────────────────────────────────────────────────

def analyse_alert_queue(n_alerts: int = 5, mock: bool = False) -> list[dict]:
    """Generate and analyse a batch of AML alerts using watsonx.ai."""
    print(f"\n  Analysing {n_alerts} alerts with IBM watsonx Granite...\n")
    results = []

    for i in range(n_alerts):
        alert = generate_alert_summary()
        print(f"  [{i+1}/{n_alerts}] Analysing alert for customer {alert['customer_id']} "
              f"(Score: {alert['composite_score']}, Tier: {alert['risk_tier']})...")

        insight = generate_watsonx_insight(alert, mock=mock)
        results.append({
            "alert": alert,
            "watsonx_insight": insight,
        })

    return results


def print_results(results: list[dict]):
    print("\n" + "═" * 70)
    print("  IBM watsonx AML INSIGHT REPORT")
    print("  Granite Foundation Model — Compliance Analysis")
    print("═" * 70)

    for i, r in enumerate(results, 1):
        alert = r["alert"]
        print(f"\n  ALERT {i} — Customer {alert['customer_id']}")
        print(f"  Risk Tier: {alert['risk_tier']}  |  Score: {alert['composite_score']}/100")
        print(f"  Flags: {', '.join(alert['flag_reasons'])}")
        print(f"  Amount: ${alert['total_flagged_amount']:,.2f}  |  Txns: {alert['flagged_transactions']}")
        print(f"\n  watsonx INSIGHT:")
        for line in r["watsonx_insight"].split('\n'):
            if line.strip():
                print(f"    {line}")
        print()

    print("═" * 70)
    print("\n  IBM VALUE PROPOSITION DEMONSTRATED:")
    print("  → watsonx.ai generates structured compliance insights from raw alert data")
    print("  → Reduces analyst time on routine alerts by automating initial assessment")
    print("  → Grounds recommendations in regulatory context (PCMLTFA, FINTRAC)")
    print("  → Directly addresses TD Bank's $3B AML compliance overhaul use case")


def main():
    parser = argparse.ArgumentParser(description="IBM watsonx AML Analytics Demo")
    parser.add_argument("--mock",    action="store_true")
    parser.add_argument("--export",  action="store_true")
    parser.add_argument("--alerts",  type=int, default=3)
    args = parser.parse_args()

    if not (IBM_API_KEY and IBM_PROJECT_ID) and not args.mock:
        print("⚠  Running in mock mode (set IBM_API_KEY and IBM_PROJECT_ID for live mode)\n")
        args.mock = True

    print("━" * 50)
    print("  IBM watsonx AML ANALYTICS DEMO")
    print(f"  Model: {WATSONX_MODEL}")
    print(f"  Mode: {'Mock' if args.mock else 'Live watsonx.ai'}")
    print("━" * 50)

    results = analyse_alert_queue(n_alerts=args.alerts, mock=args.mock)
    print_results(results)

    if args.export:
        import csv
        from pathlib import Path
        Path("data").mkdir(exist_ok=True)
        with open("data/watsonx_aml_insights.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["customer_id", "risk_tier", "score", "flags",
                             "amount", "insight"])
            for r in results:
                a = r["alert"]
                writer.writerow([a["customer_id"], a["risk_tier"], a["composite_score"],
                                 "|".join(a["flag_reasons"]), a["total_flagged_amount"],
                                 r["watsonx_insight"].replace("\n", " ")])
        print("\n  Exported to data/watsonx_aml_insights.csv")


if __name__ == "__main__":
    main()
