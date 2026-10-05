"""Domain constants: career stages, mentoring defaults, presets and limits.

No Streamlit imports; usable by core, repos, services and tests.
"""

from __future__ import annotations

CAREER_STAGES: tuple[str, ...] = (
    "Undergrad",
    "Master's",
    "PhD",
    "Postdoc",
    "Faculty",
    "Industry researcher",
)

STAGE_MENTORING_DEFAULTS: dict[str, tuple[bool, bool]] = {
    "Undergrad": (True, False),
    "Master's": (True, False),
    "Postdoc": (False, True),
    "Faculty": (False, True),
    "Industry researcher": (False, True),
}

PRESET_INTERESTS: tuple[str, ...] = (
    "Human-computer interaction",
    "Machine learning",
    "Computational social science",
    "Natural language processing",
    "Digital health",
    "Science and technology studies",
    "Bioinformatics",
    "Data visualization",
)

PRESET_SKILLS: tuple[str, ...] = (
    "Surveys",
    "Interviews",
    "Regression",
    "Thematic analysis",
    "Python",
    "R",
    "NVivo",
    "Systematic review",
)

PRESET_OFFERS: tuple[str, ...] = (
    "Methods training",
    "Co-authorship",
    "Guidance",
    "Literature review supervision",
    "Grant writing advice",
    "Code review",
    "Study design feedback",
    "Career mentorship",
)

PRESET_NEEDS: tuple[str, ...] = (
    "Data collection",
    "Lit review",
    "Coding",
    "Transcription",
    "Survey distribution",
    "Statistical analysis",
    "Participant recruitment",
    "Experiment setup",
)

METHODS_LABELS: tuple[str, ...] = (
    "qualitative",
    "quantitative",
    "mixed",
)

TEXT_LIMITS: dict[str, int] = {
    "full_name": 120,
    "institution": 2000,
    "education": 2000,
    "experience": 2000,
    "bio": 2000,
    "looking_for": 2000,
}

LIST_MAX_ITEMS = 20
LIST_ITEM_MAX_LEN = 80
