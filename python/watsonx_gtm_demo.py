"""
watsonx_gtm_demo.py
-------------------
IBM watsonx Enterprise AI Demo — Salesforce + watsonx GTM Analytics

Extends the RevOps GTM pipeline by using watsonx.ai to generate natural-language
summaries of revenue analytics — the exact kind of AI-augmented sales operations
IBM is building for its Salesforce practice clients.

Relevant to:
  - Salesforce Consulting & GTM Associate
  - Data Services Developer Associate
  - Platform Developer

Usage:
    python python/watsonx_gtm_demo.py          # full demo
    python python/watsonx_gtm_demo.py --mock   # no API key needed
"""

from __future__ import annotations
import argparse
import os
import random
from dataclasses import dataclass

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

rng = random.Random(42)

# ── Synthetic Salesforce-mirrored GTM data ────────────────────────────────────
# Mirrors Account, Opportunity, and Case objects in Salesforce

SEGMENTS = ["Enterprise", "Mid-Market", "SMB"]
STAGES   = ["Prospecting", "Discovery", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
SOURCES  = ["Inbound", "Outbound SDR", "Partner", "Event", "Referral"]

def generate_gtm_snapshot() -> dict:
    """Generate a Salesforce-style GTM pipeline snapshot."""
    accounts = []
    for i in range(15):
        seg = rng.choice(SEGMENTS)
        arr = rng.randint(20000, 250000) if seg == "Enterprise" else \
              rng.randint(5000, 50000)  if seg == "Mid-Market" else \
              rng.randint(1000, 15000)
        accounts.append({
            "account_id": f"ACC{i+1:03d}",
            "segment": seg,
            "arr_cad": arr,
            "health_score": rng.randint(40, 95),
            "open_cases": rng.randint(0, 5),
        })

    opportunities = []
    for i in range(20):
        acct = rng.choice(accounts)
        stage = rng.choice(STAGES)
        opportunities.append({
            "opp_id": f"OPP{i+1:03d}",
            "account_id": acct["account_id"],
            "segment": acct["segment"],
            "stage": stage,
            "amount_cad": rng.randint(5000, 120000),
            "close_probability": {"Prospecting":10,"Discovery":25,"Proposal":50,
                                  "Negotiation":75,"Closed Won":100,"Closed Lost":0}[stage],
            "lead_source": rng.choice(SOURCES),
        })

    # Compute KPIs
    total_pipeline = sum(o["amount_cad"] for o in opportunities
                         if o["stage"] not in ("Closed Won","Closed Lost"))
    won_arr = sum(o["amount_cad"] for o in opportunities if o["stage"] == "Closed Won")
    lost_arr = sum(o["amount_cad"] for o in opportunities if o["stage"] == "Closed Lost")
    win_rate = round(won_arr / (won_arr + lost_arr) * 100 if (won_arr + lost_arr) > 0 else 0, 1)
    avg_deal = round(sum(o["amount_cad"] for o in opportunities) / len(opportunities))
    top_source = max(SOURCES, key=lambda s: sum(o["amount_cad"] for o in opportunities if o["lead_source"]==s))
    at_risk = [a for a in accounts if a["health_score"] < 60]

    return {
        "total_pipeline_cad": total_pipeline,
        "won_arr_cad": won_arr,
        "win_rate_pct": win_rate,
        "avg_deal_size_cad": avg_deal,
        "top_lead_source": top_source,
        "at_risk_accounts": len(at_risk),
        "total_accounts": len(accounts),
        "open_opportunities": len([o for o in opportunities if o["stage"] not in ("Closed Won","Closed Lost")]),
        "segment_breakdown": {
            seg: sum(o["amount_cad"] for o in opportunities if o["segment"]==seg)
            for seg in SEGMENTS
        },
    }


GTM_PROMPT = """You are a senior revenue operations analyst. Review the following
GTM pipeline snapshot and provide a concise executive summary with:
1. Key performance highlights (2 sentences)
2. Primary risk or opportunity
3. One recommended action for the sales team

Pipeline Snapshot:
{snapshot}

Executive Summary:"""


def generate_gtm_insight(snapshot: dict, mock: bool = False) -> str:
    import json
    prompt = GTM_PROMPT.format(snapshot=json.dumps(snapshot, indent=2))

    if mock or not (IBM_API_KEY and IBM_PROJECT_ID and WATSONX_AVAILABLE):
        return (
            f"HIGHLIGHTS: Pipeline totals ${snapshot['total_pipeline_cad']:,.0f} CAD with "
            f"a {snapshot['win_rate_pct']}% win rate and ${snapshot['avg_deal_size_cad']:,.0f} "
            f"average deal size. {snapshot['top_lead_source']} is the highest-value lead source "
            f"and should receive increased investment.\n"
            f"PRIMARY RISK: {snapshot['at_risk_accounts']} accounts (of {snapshot['total_accounts']}) "
            f"have health scores below 60, representing churn exposure that could erode ARR.\n"
            f"RECOMMENDED ACTION: Prioritise QBRs with at-risk accounts this quarter; "
            f"assign a dedicated CSM to each account with health score under 55 to prevent churn "
            f"before renewal cycles begin."
        )

    credentials = Credentials(url=IBM_URL, api_key=IBM_API_KEY)
    client = APIClient(credentials=credentials, project_id=IBM_PROJECT_ID)
    model = ModelInference(
        model_id=WATSONX_MODEL,
        api_client=client,
        params={GenParams.MAX_NEW_TOKENS: 200, GenParams.TEMPERATURE: 0.3}
    )
    return model.generate_text(prompt=prompt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    if not (IBM_API_KEY and IBM_PROJECT_ID) and not args.mock:
        print("⚠  Running in mock mode\n")
        args.mock = True

    print("━" * 50)
    print("  IBM watsonx + SALESFORCE GTM ANALYTICS")
    print("  Revenue Operations AI Demo")
    print("━" * 50)

    snapshot = generate_gtm_snapshot()

    print(f"\n  PIPELINE SNAPSHOT")
    print(f"  Total pipeline:     ${snapshot['total_pipeline_cad']:>10,.0f} CAD")
    print(f"  Won ARR:            ${snapshot['won_arr_cad']:>10,.0f} CAD")
    print(f"  Win rate:           {snapshot['win_rate_pct']:>9.1f}%")
    print(f"  Avg deal size:      ${snapshot['avg_deal_size_cad']:>10,.0f} CAD")
    print(f"  Top lead source:    {snapshot['top_lead_source']:>12}")
    print(f"  At-risk accounts:   {snapshot['at_risk_accounts']:>12}")
    print(f"\n  Segment breakdown:")
    for seg, val in snapshot["segment_breakdown"].items():
        print(f"    {seg:<15} ${val:>10,.0f}")

    print(f"\n  Generating watsonx executive insight...\n")
    insight = generate_gtm_insight(snapshot, mock=args.mock)

    print("  watsonx EXECUTIVE SUMMARY:")
    for line in insight.split('\n'):
        if line.strip():
            print(f"    {line}")

    print("\n  ─────────────────────────────────────────────")
    print("  Salesforce objects mirrored: Account · Opportunity · Case")
    print("  SOQL equivalents documented in methodology.md")
    print("  watsonx.ai model: IBM Granite 13B Instruct")


if __name__ == "__main__":
    main()
