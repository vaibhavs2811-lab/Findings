"""Repo hygiene: no secret material in tracked files; keep-alive workflow shape."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = "tests/test_repo_hygiene.py"

SECRET_PATTERNS = {
    "supabase secret key": re.compile(r"sb_secret_[A-Za-z0-9_\-]{16,}"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}"),
    "google api key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "brevo smtp key": re.compile(r"xsmtpsib-[A-Za-z0-9\-]{16,}"),
}
# .streamlit/secrets.toml is committed on purpose (URL + publishable key only).
PUBLISHABLE_KEY = re.compile(r"sb_publishable_[A-Za-z0-9_\-]{16,}")
PUBLISHABLE_ALLOWED = {".streamlit/secrets.toml"}


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line]


def _tracked_texts():
    for rel in _tracked_files():
        path = ROOT / rel
        if rel == SELF or not path.is_file():
            continue
        try:
            yield rel, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


def test_local_demo_creds_not_tracked():
    assert "scripts/local.toml" not in _tracked_files()


def test_no_secret_material_in_tracked_files():
    hits = []
    for rel, text in _tracked_texts():
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                hits.append(f"{rel}: {name}")
        if rel not in PUBLISHABLE_ALLOWED and PUBLISHABLE_KEY.search(text):
            hits.append(f"{rel}: supabase publishable key outside secrets.toml")
    assert not hits, hits


def test_no_sb_secret_prefix_with_value_in_tracked_files():
    for rel, text in _tracked_texts():
        assert not re.search(r"sb_secret_\w{8,}", text), rel


def test_keepalive_workflow_shape():
    text = (ROOT / ".github/workflows/keepalive.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" in text
    assert '"17 6 * * *"' in text
    assert "rest/v1/keepalive" in text
    assert "permissions: {}" in text
    assert "--fail" in text
    assert "uses:" not in text  # no third-party actions, no checkout
    names = set(re.findall(r"secrets\.([A-Za-z0-9_]+)", text))
    assert names == {"SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY"}
    # secrets only via env, never interpolated inside the run script
    assert "secrets." not in text.split("run: |", 1)[1]
