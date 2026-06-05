# IBM watsonx Enterprise AI Demo

> Agentic AI meets enterprise analytics — automated compliance monitoring, prompt engineering, and revenue intelligence, all powered by a foundation model. Deployed on IBM Cloud Code Engine. CI/CD via GitHub Actions.

**Live demo:** [watsonx-insight-hub.lovable.app/](https://watsonx-insight-hub.lovable.app/)
**Deployed:** IBM Cloud Code Engine · Docker containerised

## Quick start

    pip install -r requirements.txt
    python python/watsonx_prompt_eval.py --mock
    python python/watsonx_aml_demo.py --mock
    python python/watsonx_gtm_demo.py --mock
    python python/watsonx_payments_demo.py --mock

## Four demos

| Demo | File | What it does |
|---|---|---|
| Prompt Evaluation | watsonx_prompt_eval.py | 4 variants × 5 cases × 4 scoring dimensions |
| AML Analytics | watsonx_aml_demo.py | AI-generated compliance insights from alert data |
| GTM Analytics | watsonx_gtm_demo.py | Salesforce-mirrored pipeline with AI executive summary |
| Payments & Digital Assets | watsonx_payments_demo.py | ISO 20022 · CBDC · stablecoin compliance analytics |

## CI/CD

push to main → test all demos → Docker build → IBM Cloud Code Engine deploy

See .github/workflows/deploy-ibm-cloud.yml

## Tech stack

Foundation model: Granite 13B Instruct via watsonx.ai SDK · Python · pandas · Docker · IBM Cloud Code Engine · GitHub Actions · Ruby on Rails (rails-demo/)

All data is synthetically generated.
