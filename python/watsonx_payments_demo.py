"""
watsonx_payments_demo.py
------------------------
IBM watsonx Enterprise AI Demo — Payments & Digital Assets Analytics

Extends the GTM demo with payments and digital asset use cases —
directly relevant to IBM Payments Centre Strategy Associate role.

Covers:
  - Payment transaction risk scoring (card, wire, crypto)
  - Digital asset (stablecoin / CBDC) transaction patterns
  - Cross-border payment analytics
  - AI-generated payments compliance insights

IBM context: IBM's Payments Centre works with major Canadian banks
on ISO 20022 migration, real-time payments (Lynx/RTP), and emerging
CBDC infrastructure. This demo shows awareness of that landscape.

Usage:
    python python/watsonx_payments_demo.py --mock
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

# ── Payment types including digital assets ─────────────────────────────────────
PAYMENT_TYPES = [
    "Interac e-Transfer",
    "SWIFT Wire",
    "Visa Debit",
    "Mastercard Credit",
    "ACH Direct Debit",
    "CBDC Transfer",          # Central Bank Digital Currency
    "Stablecoin (USDC)",      # Digital asset
    "Lynx RTGS",              # Canada's large-value payment system
    "ISO 20022 Credit Transfer",  # New standard IBM clients are migrating to
]

HIGH_RISK_COUNTRIES = ["Cayman Islands", "Panama", "Nigeria", "Belarus"]
CURRENCIES = ["CAD", "USD", "EUR", "GBP", "USDC", "eCAD"]  # eCAD = hypothetical CBDC


@dataclass
class PaymentTransaction:
    txn_id:           str
    payment_type:     str
    amount:           float
    currency:         str
    originating_country: str
    destination_country: str
    is_digital_asset: bool
    risk_indicators:  list[str]
    risk_score:       int


def generate_payment_batch(n: int = 10) -> list[PaymentTransaction]:
    """Generate a realistic mix of traditional and digital asset payments."""
    payments = []
    for i in range(n):
        ptype = rng.choice(PAYMENT_TYPES)
        is_digital = ptype in ("CBDC Transfer", "Stablecoin (USDC)")
        currency = "USDC" if "USDC" in ptype else \
                   "eCAD" if "CBDC" in ptype else \
                   rng.choice(["CAD", "USD", "EUR"])

        amount = rng.uniform(100, 500000) if not is_digital else \
                 rng.uniform(1000, 2000000)  # digital asset txns tend larger

        dest_country = rng.choices(
            ["Canada", "United States", "United Kingdom"] + HIGH_RISK_COUNTRIES,
            weights=[50, 25, 10, 5, 5, 3, 2],
            k=1
        )[0]

        # Risk indicators
        indicators = []
        if dest_country in HIGH_RISK_COUNTRIES:
            indicators.append("HIGH_RISK_JURISDICTION")
        if 9500 <= amount <= 9999.99:
            indicators.append("STRUCTURING_PATTERN")
        if is_digital and amount > 100000:
            indicators.append("LARGE_DIGITAL_ASSET_TRANSFER")
        if ptype == "SWIFT Wire" and dest_country != "Canada":
            indicators.append("CROSS_BORDER_WIRE")

        risk_score = 20 + len(indicators) * 25 + (10 if is_digital else 0)
        risk_score = min(risk_score, 100)

        payments.append(PaymentTransaction(
            txn_id=f"PAY{i+1:04d}",
            payment_type=ptype,
            amount=round(amount, 2),
            currency=currency,
            originating_country="Canada",
            destination_country=dest_country,
            is_digital_asset=is_digital,
            risk_indicators=indicators,
            risk_score=risk_score,
        ))
    return payments


PAYMENTS_PROMPT = """You are a payments compliance expert at a major Canadian bank.
Analyse the following payment transaction batch and provide:
1. Key risk observations (2-3 sentences)
2. Digital asset specific considerations (1-2 sentences)
3. ISO 20022 / regulatory compliance note

Batch summary:
{summary}

Analysis:"""


def generate_payment_insight(payments: list[PaymentTransaction], mock: bool = False) -> str:
    total    = len(payments)
    digital  = sum(1 for p in payments if p.is_digital_asset)
    high_risk = sum(1 for p in payments if p.risk_score >= 60)
    total_val = sum(p.amount for p in payments)
    cross_border = sum(1 for p in payments if p.destination_country != "Canada")

    summary = {
        "total_transactions": total,
        "digital_asset_transactions": digital,
        "high_risk_transactions": high_risk,
        "cross_border_transactions": cross_border,
        "total_value_cad": round(total_val, 2),
        "payment_types": list(set(p.payment_type for p in payments)),
        "currencies_used": list(set(p.currency for p in payments)),
        "top_risk_indicators": list(set(
            ind for p in payments for ind in p.risk_indicators
        )),
    }

    import json
    prompt = PAYMENTS_PROMPT.format(summary=json.dumps(summary, indent=2))

    if mock or not (IBM_API_KEY and IBM_PROJECT_ID and WATSONX_AVAILABLE):
        return (
            f"RISK OBSERVATIONS: The batch shows {high_risk}/{total} high-risk transactions "
            f"({high_risk/total*100:.0f}%), with {cross_border} cross-border payments "
            f"totalling ${total_val:,.0f} CAD. Structuring patterns and high-risk jurisdiction "
            f"exposure require priority review.\n\n"
            f"DIGITAL ASSET CONSIDERATIONS: {digital} digital asset transactions "
            f"(CBDC/stablecoin) detected. These fall under FINTRAC's updated guidance on "
            f"virtual currency reporting (effective 2024). Stablecoin transfers above $10,000 "
            f"require the same CTR treatment as cash transactions.\n\n"
            f"ISO 20022 NOTE: Cross-border SWIFT transactions should be reviewed for "
            f"ISO 20022 compliance. Canada's Lynx RTGS migration to ISO 20022 is complete; "
            f"legacy MT message formats in this batch require enrichment before onward routing."
        )

    credentials = Credentials(url=IBM_URL, api_key=IBM_API_KEY)
    client = APIClient(credentials=credentials, project_id=IBM_PROJECT_ID)
    model = ModelInference(
        model_id=WATSONX_MODEL,
        api_client=client,
        params={GenParams.MAX_NEW_TOKENS: 250, GenParams.TEMPERATURE: 0.2}
    )
    return model.generate_text(prompt=prompt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--n",    type=int, default=10)
    args = parser.parse_args()

    if not (IBM_API_KEY and IBM_PROJECT_ID) and not args.mock:
        print("⚠  Running in mock mode\n")
        args.mock = True

    print("━" * 55)
    print("  PAYMENTS & DIGITAL ASSETS ANALYTICS DEMO")
    print("  AI-powered payments compliance analysis")
    print("━" * 55)

    payments = generate_payment_batch(args.n)

    print(f"\n  TRANSACTION BATCH ({len(payments)} payments)")
    print(f"  {'ID':<10} {'Type':<25} {'Amount':>12} {'Currency':>8} {'Risk':>5}")
    print("  " + "─" * 65)
    for p in payments:
        flag = "⚠" if p.risk_indicators else " "
        digital_flag = "🔗" if p.is_digital_asset else "  "
        print(f"  {p.txn_id:<10} {p.payment_type:<25} "
              f"${p.amount:>11,.0f} {p.currency:>8} {p.risk_score:>4}% {flag}{digital_flag}")

    print(f"\n  Generating payments compliance insight...")
    insight = generate_payment_insight(payments, mock=args.mock)
    print(f"\n  AI COMPLIANCE INSIGHT:")
    for line in insight.split('\n'):
        if line.strip():
            print(f"    {line}")

    print("\n  ─────────────────────────────────────────────────")
    print("  Payment types covered: Traditional · ISO 20022 · CBDC · Stablecoin")
    print("  Regulatory framework: PCMLTFA · FINTRAC · Lynx RTGS · ISO 20022")


if __name__ == "__main__":
    main()
