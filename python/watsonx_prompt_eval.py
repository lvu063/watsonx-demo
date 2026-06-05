"""
watsonx_prompt_eval.py
----------------------
IBM watsonx Enterprise AI Demo — Prompt Evaluation Framework

Mirrors the Cohere prompt evaluation project but using IBM's watsonx.ai platform.
Demonstrates IBM-specific product knowledge for:
  - AI Driven Skills Growth Developer
  - Platform Developer
  - Data Services Developer Associate

The core insight IBM's AI adoption research surfaces: enterprises fail to get
ROI from AI because they vibe-check prompts rather than evaluate them
systematically. This framework is the antidote.

Usage:
    python python/watsonx_prompt_eval.py              # full eval
    python python/watsonx_prompt_eval.py --mock       # no API key needed
    python python/watsonx_prompt_eval.py --export     # save results CSV
"""

from __future__ import annotations
import argparse
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ── IBM watsonx SDK (pip install ibm-watsonx-ai) ──────────────────────────────
try:
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    WATSONX_AVAILABLE = True
except ImportError:
    WATSONX_AVAILABLE = False

import os
import random

# ── Configuration ─────────────────────────────────────────────────────────────
IBM_API_KEY    = os.getenv("IBM_API_KEY", "")
IBM_PROJECT_ID = os.getenv("IBM_PROJECT_ID", "")
IBM_URL        = os.getenv("IBM_URL", "https://us-south.ml.cloud.ibm.com")

# watsonx.ai model — IBM's flagship foundation model
# Granite is IBM's enterprise-grade LLM family
WATSONX_MODEL = "ibm/granite-13b-instruct-v2"

# ── Test cases — enterprise AML/fraud domain ──────────────────────────────────
TEST_CASES = [
    {
        "id": "TC-001",
        "query": "What is structuring in the context of AML compliance?",
        "expected_keywords": ["structuring", "threshold", "$10,000", "CTR", "PCMLTFA", "reporting"],
        "difficulty": "foundational",
    },
    {
        "id": "TC-002",
        "query": "How do you calculate a customer's AML risk score?",
        "expected_keywords": ["KYC", "PEP", "transaction", "risk", "score", "factors"],
        "difficulty": "analytical",
    },
    {
        "id": "TC-003",
        "query": "What is a politically exposed person and why does it matter for due diligence?",
        "expected_keywords": ["PEP", "politically exposed", "enhanced due diligence", "risk", "government"],
        "difficulty": "foundational",
    },
    {
        "id": "TC-004",
        "query": "Explain velocity analysis in fraud detection.",
        "expected_keywords": ["velocity", "frequency", "window", "transactions", "pattern", "anomaly"],
        "difficulty": "analytical",
    },
    {
        "id": "TC-005",
        "query": "What are the key indicators of money laundering in wire transfers?",
        "expected_keywords": ["wire", "jurisdiction", "beneficial owner", "layering", "origin", "suspicious"],
        "difficulty": "advanced",
    },
]

# ── Prompt variants ────────────────────────────────────────────────────────────
PROMPT_VARIANTS = {
    "v1_baseline": {
        "label": "Baseline (no scaffolding)",
        "description": "Minimal instruction — what does the model do with no guidance?",
        "template": "{query}",
    },
    "v2_role": {
        "label": "Role assignment",
        "description": "Assign AML compliance expert role — does it improve precision?",
        "template": (
            "You are a senior AML compliance analyst at a major Canadian bank. "
            "Answer the following question accurately and concisely, using correct "
            "regulatory terminology.\n\nQuestion: {query}"
        ),
    },
    "v3_cot": {
        "label": "Chain-of-thought",
        "description": "Reason step-by-step before answering — reduces confident wrong answers.",
        "template": (
            "You are an AML compliance expert. Think through this step by step "
            "before giving your final answer.\n\n"
            "Question: {query}\n\n"
            "Let me think through this:\n"
            "1. What is the core concept being asked about?\n"
            "2. What are the key regulatory or technical facts?\n"
            "3. What is the most accurate and complete answer?\n\n"
            "Final answer:"
        ),
    },
    "v4_few_shot": {
        "label": "Few-shot examples",
        "description": "Two exemplars anchor format and depth — best for consistency.",
        "template": (
            "Answer compliance questions accurately using regulatory terminology.\n\n"
            "Q: What is a Currency Transaction Report?\n"
            "A: A Currency Transaction Report (CTR) is a mandatory report filed with "
            "FINTRAC when a financial institution processes cash transactions of $10,000 "
            "CAD or more. The requirement exists under PCMLTFA to detect structuring "
            "and other cash-intensive money laundering patterns.\n\n"
            "Q: What does KYC stand for and why is it required?\n"
            "A: KYC (Know Your Customer) refers to the due diligence processes financial "
            "institutions must follow to verify customer identity and assess risk. "
            "Under FINTRAC guidance, KYC forms the foundation of AML programs, enabling "
            "institutions to detect unusual activity against an established baseline.\n\n"
            "Q: {query}\n"
            "A:"
        ),
    },
}

# ── Scoring ────────────────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    variant_id: str
    variant_label: str
    test_case_id: str
    query: str
    response: str
    latency_ms: float
    keyword_score: float     # keyword coverage
    conciseness_score: float # length efficiency
    hallucination_proxy: float  # confidence-to-correctness proxy
    format_score: float      # structured response quality
    overall_score: float = field(init=False)

    def __post_init__(self):
        self.overall_score = round(
            self.keyword_score * 0.35 +
            self.hallucination_proxy * 0.30 +
            self.conciseness_score * 0.20 +
            self.format_score * 0.15, 3
        )


def score_keyword_coverage(response: str, expected: list[str]) -> float:
    """What fraction of expected keywords appear in the response?"""
    if not expected:
        return 1.0
    resp_lower = response.lower()
    hits = sum(1 for kw in expected if kw.lower() in resp_lower)
    return round(hits / len(expected), 3)


def score_conciseness(response: str) -> float:
    """Penalise excessive length — verbose hedging is a reliability signal."""
    words = len(response.split())
    if words <= 80:   return 1.0
    if words <= 150:  return 0.85
    if words <= 250:  return 0.70
    if words <= 400:  return 0.55
    return 0.40


def score_hallucination_proxy(response: str, keywords: list[str]) -> float:
    """
    Proxy: high confidence + correct keywords → likely accurate.
    Hedge words without keywords → possibly hallucinating.
    """
    hedges = ["i think", "i believe", "i'm not sure", "possibly", "might be", "could be"]
    resp_lower = response.lower()
    hedge_count = sum(1 for h in hedges if h in resp_lower)
    kw_score = score_keyword_coverage(response, keywords)
    base = kw_score
    penalty = hedge_count * 0.05
    return max(0.0, round(base - penalty, 3))


def score_format(response: str) -> float:
    """Does the response have clear structure?"""
    score = 0.7  # base
    if len(response.split('.')) > 2:  score += 0.1   # multiple sentences
    if any(c in response for c in [':', '-', '•']): score += 0.1  # structure markers
    if response[0].isupper() and response.rstrip().endswith('.'): score += 0.1
    return min(1.0, round(score, 3))


# ── Model call ─────────────────────────────────────────────────────────────────

def call_watsonx(prompt: str, mock: bool = False) -> tuple[str, float]:
    """Call watsonx.ai or return mock response."""
    if mock or not (IBM_API_KEY and IBM_PROJECT_ID and WATSONX_AVAILABLE):
        # Deterministic mock — realistic AML compliance responses
        mock_responses = {
            "structuring": "Structuring is the practice of breaking large cash transactions into smaller amounts to stay below the $10,000 CTR threshold under PCMLTFA s.9. It is a federal offence and a key indicator investigators escalate to FINTRAC.",
            "risk score": "AML risk scoring combines multiple KYC factors: the customer's baseline risk rating from onboarding, their transaction behaviour (flagged ratio), PEP status, high-risk jurisdiction exposure, and historical FINTRAC escalations.",
            "politically exposed": "A PEP (Politically Exposed Person) is someone who holds or has held a prominent public function. PEPs require Enhanced Due Diligence (EDD) under FINTRAC guidance due to heightened corruption and bribery risk.",
            "velocity": "Velocity analysis detects customers with unusually high transaction frequency within a rolling time window (e.g., 7 days). High velocity can indicate account takeover, smurfing, or layering.",
            "wire": "Key laundering indicators in wire transfers include: counterparties in FATF high-risk jurisdictions, transactions with no clear business purpose, round-number amounts, and patterns of layering through multiple accounts.",
        }
        t0 = time.time()
        response = next((v for k, v in mock_responses.items() if k in prompt.lower()),
                        "This is a mock response demonstrating the evaluation framework.")
        latency = (time.time() - t0) * 1000 + random.uniform(200, 500)
        return response, round(latency, 1)

    # Real watsonx.ai call
    credentials = Credentials(url=IBM_URL, api_key=IBM_API_KEY)
    client = APIClient(credentials=credentials, project_id=IBM_PROJECT_ID)
    model = ModelInference(
        model_id=WATSONX_MODEL,
        api_client=client,
        params={
            GenParams.MAX_NEW_TOKENS: 300,
            GenParams.MIN_NEW_TOKENS: 30,
            GenParams.TEMPERATURE: 0.1,  # low temperature for factual compliance queries
            GenParams.TOP_P: 0.9,
        }
    )
    t0 = time.time()
    result = model.generate_text(prompt=prompt)
    latency = (time.time() - t0) * 1000
    return result, round(latency, 1)


# ── Evaluation runner ──────────────────────────────────────────────────────────

def run_evaluation(mock: bool = False) -> list[EvalResult]:
    results = []
    total = len(PROMPT_VARIANTS) * len(TEST_CASES)
    count = 0

    for variant_id, variant in PROMPT_VARIANTS.items():
        for tc in TEST_CASES:
            count += 1
            prompt = variant["template"].format(query=tc["query"])
            response, latency = call_watsonx(prompt, mock=mock)

            result = EvalResult(
                variant_id=variant_id,
                variant_label=variant["label"],
                test_case_id=tc["id"],
                query=tc["query"],
                response=response,
                latency_ms=latency,
                keyword_score=score_keyword_coverage(response, tc["expected_keywords"]),
                conciseness_score=score_conciseness(response),
                hallucination_proxy=score_hallucination_proxy(response, tc["expected_keywords"]),
                format_score=score_format(response),
            )
            results.append(result)
            print(f"  [{count}/{total}] {variant_id} × {tc['id']} → {result.overall_score:.3f}")

    return results


def print_leaderboard(results: list[EvalResult]):
    from collections import defaultdict

    variant_scores: dict[str, list[float]] = defaultdict(list)
    variant_labels: dict[str, str] = {}
    variant_latencies: dict[str, list[float]] = defaultdict(list)

    for r in results:
        variant_scores[r.variant_id].append(r.overall_score)
        variant_labels[r.variant_id] = r.variant_label
        variant_latencies[r.variant_id].append(r.latency_ms)

    ranked = sorted(
        variant_scores.items(),
        key=lambda x: sum(x[1]) / len(x[1]),
        reverse=True
    )

    medals = ["🥇", "🥈", "🥉", "   "]
    print("\n" + "═" * 72)
    print("  IBM watsonx PROMPT EVALUATION LEADERBOARD")
    print(f"  Model: {WATSONX_MODEL}  |  Test cases: {len(TEST_CASES)}")
    print("═" * 72)
    print(f"  {'Variant':<30} {'Overall':>8} {'KW':>7} {'Hall':>7} {'Lat(ms)':>9}")
    print("  " + "─" * 68)

    for i, (vid, scores) in enumerate(ranked):
        avg = sum(scores) / len(scores)
        r_sample = next(r for r in results if r.variant_id == vid)
        avg_lat = sum(variant_latencies[vid]) / len(variant_latencies[vid])
        medal = medals[i] if i < 4 else "   "
        label = variant_labels[vid]
        print(f"  {medal} {label:<28} {avg:>8.3f} {r_sample.keyword_score:>7.3f} "
              f"{r_sample.hallucination_proxy:>7.3f} {avg_lat:>9.0f}")

    print("═" * 72)
    print("\n  KEY INSIGHT FOR IBM:")
    winner_id = ranked[0][0]
    print(f"  {variant_labels[winner_id]} wins.")
    print("  IBM's AI adoption challenge: enterprises skip systematic evaluation.")
    print("  This framework is what IBM watsonx.ai needs to deliver enterprise ROI.")
    print()


def export_results(results: list[EvalResult]):
    import csv
    out = Path("data")
    out.mkdir(exist_ok=True)
    filepath = out / f"watsonx_eval_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["variant_id", "variant_label", "test_case_id", "query",
                         "keyword_score", "conciseness", "hallucination_proxy",
                         "format_score", "overall_score", "latency_ms"])
        for r in results:
            writer.writerow([r.variant_id, r.variant_label, r.test_case_id, r.query,
                             r.keyword_score, r.conciseness_score, r.hallucination_proxy,
                             r.format_score, r.overall_score, r.latency_ms])
    print(f"  Exported to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="IBM watsonx Prompt Evaluation Demo")
    parser.add_argument("--mock",   action="store_true", help="Run without API key")
    parser.add_argument("--export", action="store_true", help="Export results to CSV")
    args = parser.parse_args()

    if not (IBM_API_KEY and IBM_PROJECT_ID) and not args.mock:
        print("⚠  IBM_API_KEY or IBM_PROJECT_ID not set. Running in mock mode.")
        print("   Set env vars or use --mock flag.\n")
        args.mock = True

    print("━" * 50)
    print("  IBM watsonx ENTERPRISE AI DEMO")
    print("  Prompt Evaluation Framework")
    print(f"  Mode: {'Mock' if args.mock else 'Live watsonx.ai'}")
    print("━" * 50)
    print(f"\n  Testing {len(PROMPT_VARIANTS)} variants × {len(TEST_CASES)} cases\n")

    results = run_evaluation(mock=args.mock)
    print_leaderboard(results)

    if args.export:
        export_results(results)


if __name__ == "__main__":
    main()
