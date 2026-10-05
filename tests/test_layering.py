"""Architectural layering test.

Enforces that findings/ai, findings/services, findings/repos, and findings/core/constants.py
never import Streamlit, and ensures secrets.toml does not commit GEMINI_API_KEY.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_no_streamlit_imports_in_backend_modules():
    targets = [
        ROOT / "findings" / "ai",
        ROOT / "findings" / "services",
        ROOT / "findings" / "repos",
        ROOT / "findings" / "core" / "constants.py",
    ]

    py_files: list[Path] = []
    for target in targets:
        if target.is_file():
            py_files.append(target)
        elif target.is_dir():
            py_files.extend(target.rglob("*.py"))

    assert len(py_files) >= 5, f"Expected multiple target files, found {len(py_files)}"

    violations: list[str] = []
    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "streamlit" or alias.name.startswith("streamlit."):
                        violations.append(f"{py_file.relative_to(ROOT)} imports {alias.name}")
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and (node.module == "streamlit" or node.module.startswith("streamlit."))
            ):
                violations.append(f"{py_file.relative_to(ROOT)} imports from {node.module}")

    assert not violations, "Streamlit import violations found in backend:\n" + "\n".join(violations)


def test_secrets_toml_has_no_gemini_api_key():
    secrets_path = ROOT / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        content = secrets_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped.startswith("#"):
                assert not stripped.startswith("GEMINI_API_KEY"), (
                    "GEMINI_API_KEY must never be committed in .streamlit/secrets.toml"
                )
