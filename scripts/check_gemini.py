"""Live Gemini smoke test calling Flash-Lite models with structured output.

Resolves key from:
  1. Environment variable: GEMINI_API_KEY
  2. Global Streamlit secrets: ~/.streamlit/secrets.toml
  3. Local developer config: scripts/local.toml

Exit codes:
  0: All model checks passed
  1: Any model check failed
  2: No Gemini API key found (skip)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from findings.ai.client import TEXT_MODELS, AIUnavailable, make_client
from findings.ai.methods import suggest_methods

SAMPLE: dict[str, object] = {
    "interests": ["Public health", "Epidemiology", "Mixed methods"],
    "skills": ["Surveys", "Interviews", "Regression analysis"],
    "experience": "5 years running community health surveys and clinical interviews.",
    "bio": "Investigating social determinants of health using quantitative and qualitative data.",
    "education": "PhD in Public Health",
    "looking_for": "Collaborators with expertise in data visualization or biostatistics.",
}


def find_api_key() -> str | None:
    # 1. Environment variable
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    # 2. Global ~/.streamlit/secrets.toml
    global_secrets = Path.home() / ".streamlit" / "secrets.toml"
    if global_secrets.exists():
        try:
            with open(global_secrets, "rb") as fh:
                data = tomllib.load(fh)
                key = data.get("GEMINI_API_KEY")
                if key and str(key).strip():
                    return str(key).strip()
        except Exception:
            pass

    # 3. scripts/local.toml
    local_path = ROOT / "scripts" / "local.toml"
    if local_path.exists():
        try:
            with open(local_path, "rb") as fh:
                data = tomllib.load(fh)
                key = data.get("GEMINI_API_KEY")
                if key and str(key).strip():
                    return str(key).strip()
        except Exception:
            pass

    return None


def main() -> int:
    key = find_api_key()
    if not key:
        print("SKIP: no Gemini key")
        return 2

    client = make_client(key)
    passed = 0
    failed = 0

    for idx, model in enumerate(TEXT_MODELS, start=1):
        check_id = f"G{idx}"
        try:
            res = suggest_methods(SAMPLE, client=client, models=(model,))
            print(f"PASS {check_id} - {model}: [{res.label}] {res.reason}")
            passed += 1
        except AIUnavailable as exc:
            cause = exc.__cause__
            cause_name = type(cause).__name__ if cause else "Unknown"
            code = getattr(cause, "code", getattr(cause, "status_code", ""))
            detail = f"{cause_name} (code {code})" if code else cause_name
            print(f"FAIL {check_id} - {model}: {detail}")
            failed += 1
        except Exception as err:
            print(f"FAIL {check_id} - {model}: error {type(err).__name__}")
            failed += 1

    print(f"{passed} passed, {failed} failed")
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
