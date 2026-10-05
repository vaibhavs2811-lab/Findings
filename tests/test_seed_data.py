"""Unit tests for synthetic seed data generation, validation, and JSON dataset integrity."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from findings.ai.seed_prompt import SeedBatchResponse, SeedProfileItem, build_seed_prompt
from findings.core.constants import METHODS_LABELS
from findings.services.seed_data import (
    NAME_REGIONS,
    RESEARCH_FIELDS,
    STAGE_QUOTAS,
    build_spec_matrix,
    clean_seed_profile,
    contact_email,
    email_slug,
)

ROOT = Path(__file__).resolve().parent.parent
SEED_JSON_PATH = ROOT / "data" / "seed_profiles.json"


def test_spec_matrix_exact_counts_and_quotas():
    specs = build_spec_matrix()
    assert len(specs) == 80

    stages = Counter(s["career_stage"] for s in specs)
    for stage, target in STAGE_QUOTAS.items():
        assert stages[stage] == target, f"Stage {stage} count {stages[stage]} != {target}"

    fields = {s["field"] for s in specs}
    assert fields == set(RESEARCH_FIELDS)

    regions = {s["region"] for s in specs}
    assert regions == set(NAME_REGIONS)

    methods = Counter(s["methods_effective"] for s in specs)
    for m in METHODS_LABELS:
        assert methods[m] >= 24, f"Methods orientation {m} under-represented: {methods[m]}"


def test_spec_matrix_mentoring_rules():
    specs = build_spec_matrix()
    for s in specs:
        stage = s["career_stage"]
        seeking = s["seeking_mentor"]
        open_to = s["open_to_mentoring"]

        if stage in ("Undergrad", "Master's"):
            assert seeking is True
            assert open_to is False
        elif stage in ("Faculty", "Industry researcher"):
            assert open_to is True
            assert seeking is False
        elif stage == "Postdoc":
            assert open_to is True
        elif stage == "PhD":
            assert seeking or open_to  # At least one toggle active


def test_demo_pairs_present_and_aligned():
    specs = build_spec_matrix()
    spec_map = {s["seed_id"]: s for s in specs}

    # P1: Public Health Qual PhD + Quant Postdoc
    s1, s2 = spec_map["seed-001"], spec_map["seed-002"]
    assert s1["demo_pair"] == "P1"
    assert s2["demo_pair"] == "P1"
    assert s1["field"] == s2["field"] == "Public Health & Epidemiology"
    assert s1["career_stage"] == "PhD" and s1["methods_effective"] == "qualitative"
    assert s2["career_stage"] == "Postdoc" and s2["methods_effective"] == "quantitative"

    # P2: Faculty Mentor + Master's Mentee in AI
    s3, s4 = spec_map["seed-003"], spec_map["seed-004"]
    assert s3["demo_pair"] == "P2"
    assert s4["demo_pair"] == "P2"
    assert s3["field"] == s4["field"] == "Computer Science & AI"
    assert s3["career_stage"] == "Faculty" and s3["open_to_mentoring"] is True
    assert s4["career_stage"] == "Master's" and s4["seeking_mentor"] is True

    # P3: Industry Quant + PhD Qual in HCI
    s5, s6 = spec_map["seed-005"], spec_map["seed-006"]
    assert s5["demo_pair"] == "P3"
    assert s6["demo_pair"] == "P3"
    assert s5["field"] == s6["field"] == "Human-Computer Interaction"
    assert s5["career_stage"] == "Industry researcher" and s5["methods_effective"] == "quantitative"
    assert s6["career_stage"] == "PhD" and s6["methods_effective"] == "qualitative"


def test_email_slug_and_contact_email():
    assert email_slug("Dr. Zoë Müller") == "dr-zoe-muller"
    assert email_slug("Jean-François O'Connor") == "jean-francois-oconnor"
    assert email_slug("") == "researcher"

    email = contact_email("Dr. Zoë Müller", "seed-001")
    assert email == "dr-zoe-muller.seed001@example.org"
    assert email.endswith("@example.org")


def test_clean_seed_profile_text_safety():
    spec = {
        "seed_id": "seed-099",
        "demo_pair": None,
        "career_stage": "PhD",
        "methods_effective": "qualitative",
        "seeking_mentor": True,
        "open_to_mentoring": False,
    }

    # Bio with email -> dropped
    bad_bio = {"full_name": "Alice", "bio": "Contact me at alice@real.edu"}
    assert clean_seed_profile(bad_bio, spec) is None

    # Interests with URL -> dropped
    bad_url = {"full_name": "Alice", "interests": ["https://malicious.org/code"]}
    assert clean_seed_profile(bad_url, spec) is None

    # Valid profile -> successfully cleaned
    valid_raw = {
        "full_name": "Alice Wonderland",
        "institution": "Wonderland University",
        "bio": "Investigating fantasy narrative structures.",
        "interests": ["Narratology", "Folklore"],
        "skills": ["Close reading", "Textual analysis"],
        "contributable_skills": ["Archival indexing"],
        "want_to_learn": ["Digital humanities GIS"],
        "offers": ["Should be stripped because open_to_mentoring is False"],
    }
    cleaned = clean_seed_profile(valid_raw, spec)
    assert cleaned is not None
    assert cleaned["full_name"] == "Alice Wonderland"
    assert cleaned["email"] == "alice-wonderland.seed099@example.org"
    assert cleaned["career_stage"] == "PhD"
    assert cleaned["methods_effective"] == "qualitative"
    # Offers stripped because open_to_mentoring is False
    assert cleaned["offers"] == []
    assert cleaned["contributable_skills"] == ["Archival indexing"]


def test_seed_prompt_builder_and_schemas():
    batch = [
        {
            "seed_id": "seed-001",
            "career_stage": "PhD",
            "field": "Public Health",
            "methods_effective": "qualitative",
        }
    ]
    prompt = build_seed_prompt(batch)
    assert "seed-001" in prompt
    assert "Public Health" in prompt

    # Verify Pydantic schema validation
    item = SeedProfileItem(
        seed_id="seed-001",
        full_name="Dr. Jane Doe",
        institution="Fictional University",
        education="PhD in Public Health",
        experience="Experience summary",
        bio="Bio statement",
        looking_for="Collaborators",
        interests=["Topic A", "Topic B", "Topic C"],
        skills=["Skill 1", "Skill 2", "Skill 3"],
    )
    batch_resp = SeedBatchResponse(profiles=[item])
    assert len(batch_resp.profiles) == 1
    assert batch_resp.profiles[0].seed_id == "seed-001"


def test_committed_seed_profiles_json_integrity():
    assert SEED_JSON_PATH.exists(), "data/seed_profiles.json must exist"

    with open(SEED_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles = data.get("profiles", [])
    assert len(profiles) == 80, f"Expected 80 profiles, got {len(profiles)}"

    meta = data.get("meta", {})
    assert meta.get("count") == 80
    assert "demo_pairs" in meta

    stages = Counter(p["career_stage"] for p in profiles)
    for stage, target in STAGE_QUOTAS.items():
        assert stages[stage] == target, f"Stage {stage} count {stages[stage]} != {target}"

    methods = Counter(p["methods_effective"] for p in profiles)
    for m in METHODS_LABELS:
        assert methods[m] >= 24, f"Methods orientation {m} under-represented"

    seen_ids = set()
    for p in profiles:
        sid = p["seed_id"]
        assert sid not in seen_ids, f"Duplicate seed_id: {sid}"
        seen_ids.add(sid)

        assert p["is_synthetic"] is True
        assert p["is_complete"] is True
        assert p["email"].endswith("@example.org")

        # No real email or URL in any string field
        for k in ("full_name", "institution", "education", "experience", "bio", "looking_for"):
            val = p.get(k) or ""
            assert "http" not in val, f"URL in {sid} field {k}: {val}"

        # Give/need lists consistency
        if not p["open_to_mentoring"]:
            assert p["offers"] == [], f"Disallowed offers in {sid}"
            assert p["needs"] == [], f"Disallowed needs in {sid}"
        if not p["seeking_mentor"]:
            assert p["contributable_skills"] == [], f"Disallowed contributable_skills in {sid}"
            assert p["want_to_learn"] == [], f"Disallowed want_to_learn in {sid}"

    # Demo pairs checks
    demo_profiles = {p["seed_id"]: p for p in profiles if p.get("demo_pair")}
    assert len(demo_profiles) == 6
    assert demo_profiles["seed-001"]["demo_pair"] == "P1"
    assert demo_profiles["seed-002"]["demo_pair"] == "P1"
    assert demo_profiles["seed-003"]["demo_pair"] == "P2"
    assert demo_profiles["seed-004"]["demo_pair"] == "P2"
    assert demo_profiles["seed-005"]["demo_pair"] == "P3"
    assert demo_profiles["seed-006"]["demo_pair"] == "P3"
