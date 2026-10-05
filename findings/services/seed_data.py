"""Seed dataset specification matrix and domain validation for synthetic researcher pool.

Generates 80 diverse, reproducible specifications balancing fields, career stages,
methods orientations, and mentoring exchange roles with curated anchor demo pairs.
"""

from __future__ import annotations

import random
import re
import unicodedata
from typing import Any

from findings.core.constants import CAREER_STAGES, METHODS_LABELS

RESEARCH_FIELDS = [
    "Computer Science & AI",
    "Human-Computer Interaction",
    "Computational Biology & Genomics",
    "Cognitive Psychology",
    "Sociology & Migration Studies",
    "Economics & Game Theory",
    "Cognitive Neuroscience",
    "Public Health & Epidemiology",
    "Environmental Science & Climatology",
    "Condensed Matter & Quantum Physics",
    "Computational Linguistics",
    "Education Science & Learning Technologies",
    "Political Science & Comparative Governance",
    "Materials Science & Nanotechnology",
]

NAME_REGIONS = [
    "East Asian",
    "South Asian",
    "European (Germanic/Nordic)",
    "European (Romance)",
    "European (Slavic)",
    "Middle Eastern",
    "Latin American",
    "Sub-Saharan African",
    "North American",
    "Southeast Asian",
]

STAGE_QUOTAS = {
    "Undergrad": 10,
    "Master's": 14,
    "PhD": 18,
    "Postdoc": 14,
    "Faculty": 14,
    "Industry researcher": 10,
}

DEMO_PAIRS_META = {
    "P1": {
        "title": "Public Health Methods Complementarity (Qualitative PhD + Quantitative Postdoc)",
        "pair_ids": ["seed-001", "seed-002"],
        "field": "Public Health & Epidemiology",
    },
    "P2": {
        "title": "AI Mentorship Exchange Fit (Faculty Mentor + Master's Mentee)",
        "pair_ids": ["seed-003", "seed-004"],
        "field": "Computer Science & AI",
    },
    "P3": {
        "title": "HCI Cross-Sector Synergy (Industry Quant + PhD Qual)",
        "pair_ids": ["seed-005", "seed-006"],
        "field": "Human-Computer Interaction",
    },
}


def email_slug(name: str) -> str:
    """Generate clean ascii hyphenated slug from researcher name."""
    if not name:
        return "researcher"
    # Normalize unicode to decompose accents (e.g. ë -> e + ¨)
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", ascii_only).strip().lower()
    slug = re.sub(r"[\s-]+", "-", cleaned)
    return slug or "researcher"


def contact_email(name: str, seed_id: str) -> str:
    """Construct fictional contact email in example.org domain."""
    slug = email_slug(name)
    clean_id = re.sub(r"[^a-zA-Z0-9]", "", seed_id).lower()
    return f"{slug}.{clean_id}@example.org"


def build_spec_matrix() -> list[dict[str, Any]]:
    """Build deterministic list of 80 profile specifications using Random(42)."""
    rng = random.Random(42)
    specs: list[dict[str, Any]] = []

    # 1. Inject Curated Demo Pairs (seeds 1 to 6)
    # P1: Public health qual PhD + quant Postdoc
    specs.append({
        "seed_id": "seed-001",
        "demo_pair": "P1",
        "career_stage": "PhD",
        "methods_effective": "qualitative",
        "field": "Public Health & Epidemiology",
        "subfield": "Community health access and migrant healthcare barriers",
        "region": "Sub-Saharan African",
        "seeking_mentor": True,
        "open_to_mentoring": False,
        "guidance": "Qualitative ethnography, semi-structured interviews on maternal health access in underserved clinics.",
    })
    specs.append({
        "seed_id": "seed-002",
        "demo_pair": "P1",
        "career_stage": "Postdoc",
        "methods_effective": "quantitative",
        "field": "Public Health & Epidemiology",
        "subfield": "Spatial epidemiology and longitudinal survival modeling",
        "region": "European (Romance)",
        "seeking_mentor": False,
        "open_to_mentoring": True,
        "guidance": "Quantitative survival analysis, Bayesian spatial models of epidemic spread and clinic catchment.",
    })

    # P2: Faculty Mentor + Master's Junior in AI
    specs.append({
        "seed_id": "seed-003",
        "demo_pair": "P2",
        "career_stage": "Faculty",
        "methods_effective": "mixed",
        "field": "Computer Science & AI",
        "subfield": "Efficient transformer architectures and model evaluation",
        "region": "South Asian",
        "seeking_mentor": False,
        "open_to_mentoring": True,
        "guidance": "Offers grant proposal review and research direction; needs dataset curation and PyTorch benchmarking.",
    })
    specs.append({
        "seed_id": "seed-004",
        "demo_pair": "P2",
        "career_stage": "Master's",
        "methods_effective": "quantitative",
        "field": "Computer Science & AI",
        "subfield": "Deep learning system benchmarking and data pipelines",
        "region": "East Asian",
        "seeking_mentor": True,
        "open_to_mentoring": False,
        "guidance": "Contributes PyTorch dataset curation and benchmarking; wants to learn research formulation and grant writing.",
    })

    # P3: Industry Quant + PhD Qual in HCI
    specs.append({
        "seed_id": "seed-005",
        "demo_pair": "P3",
        "career_stage": "Industry researcher",
        "methods_effective": "quantitative",
        "field": "Human-Computer Interaction",
        "subfield": "Large-scale telemetry and A/B testing for collaborative software",
        "region": "North American",
        "seeking_mentor": False,
        "open_to_mentoring": True,
        "guidance": "Quantitative clickstream telemetry, causal inference, and user retention experiments.",
    })
    specs.append({
        "seed_id": "seed-006",
        "demo_pair": "P3",
        "career_stage": "PhD",
        "methods_effective": "qualitative",
        "field": "Human-Computer Interaction",
        "subfield": "Participatory design and contextual inquiry for remote collaboration",
        "region": "European (Germanic/Nordic)",
        "seeking_mentor": True,
        "open_to_mentoring": False,
        "guidance": "Qualitative contextual inquiry, diary studies, and co-design workshops on digital fatigue.",
    })

    # Count of stages already allocated by demo pairs
    allocated_stages = {
        "PhD": 2,
        "Postdoc": 1,
        "Faculty": 1,
        "Master's": 1,
        "Industry researcher": 1,
        "Undergrad": 0,
    }

    # 2. Generate remaining 74 profiles deterministically by stage quotas
    methods_rotator = 0
    region_rotator = 0
    field_rotator = 0
    seed_num = 7

    for stage in CAREER_STAGES:
        target_count = STAGE_QUOTAS[stage]
        current_count = allocated_stages.get(stage, 0)
        needed = target_count - current_count

        for i in range(needed):
            sid = f"seed-{seed_num:03d}"
            seed_num += 1

            method = METHODS_LABELS[methods_rotator % len(METHODS_LABELS)]
            methods_rotator += 1

            field = RESEARCH_FIELDS[field_rotator % len(RESEARCH_FIELDS)]
            field_rotator += 1

            region = NAME_REGIONS[region_rotator % len(NAME_REGIONS)]
            region_rotator += 1

            # Mentoring role determination
            if stage in ("Undergrad", "Master's"):
                seeking = True
                open_to = False
            elif stage in ("Faculty", "Industry researcher"):
                seeking = False
                open_to = True
            elif stage == "Postdoc":
                open_to = True
                seeking = (i % 3 == 0)  # Every third postdoc also seeks
            else:  # PhD
                pattern = i % 3
                if pattern == 0:
                    seeking, open_to = True, False
                elif pattern == 1:
                    seeking, open_to = False, True
                else:
                    seeking, open_to = True, True

            specs.append({
                "seed_id": sid,
                "demo_pair": None,
                "career_stage": stage,
                "methods_effective": method,
                "field": field,
                "subfield": f"Core research in {field.lower()} focusing on {method} methods",
                "region": region,
                "seeking_mentor": seeking,
                "open_to_mentoring": open_to,
                "guidance": f"Researcher in {field} applying {method} methodologies.",
            })

    # Shuffle spec order with fixed seed (preserving seed_id lookup)
    # Keep the demo pairs easily identifiable while mixing stages
    non_demo = specs[6:]
    rng.shuffle(non_demo)
    return specs[:6] + non_demo


def clean_seed_profile(raw: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and sanitize a generated profile against its specification.

    Enforces code-as-truth for stage, methods, and mentoring toggles.
    Rejects profiles with emails or URLs in text.
    Clears disallowed give/need lists based on mentoring toggles.
    """
    # 1. Text safety check: drop if '@' or 'http' appears in any text
    for key in ("full_name", "institution", "education", "experience", "bio", "looking_for"):
        val = str(raw.get(key) or "")
        if "@" in val or "http://" in val or "https://" in val:
            return None

    for list_key in ("interests", "skills", "offers", "needs", "contributable_skills", "want_to_learn"):
        for item in raw.get(list_key) or []:
            val = str(item)
            if "@" in val or "http://" in val or "https://" in val:
                return None

    name = str(raw.get("full_name") or "").strip()
    if not name or len(name) < 2:
        return None

    # 2. Extract allowed give/need lists according to spec toggles
    open_to = spec["open_to_mentoring"]
    seeking = spec["seeking_mentor"]

    offers = [str(x).strip() for x in (raw.get("offers") or []) if str(x).strip()] if open_to else []
    needs = [str(x).strip() for x in (raw.get("needs") or []) if str(x).strip()] if open_to else []
    contributable = [
        str(x).strip() for x in (raw.get("contributable_skills") or []) if str(x).strip()
    ] if seeking else []
    want_to_learn = [
        str(x).strip() for x in (raw.get("want_to_learn") or []) if str(x).strip()
    ] if seeking else []

    interests = [str(x).strip() for x in (raw.get("interests") or []) if str(x).strip()]
    skills = [str(x).strip() for x in (raw.get("skills") or []) if str(x).strip()]

    # 3. Assemble validated profile
    seed_id = spec["seed_id"]
    email = contact_email(name, seed_id)

    return {
        "seed_id": seed_id,
        "demo_pair": spec.get("demo_pair"),
        "full_name": name,
        "email": email,
        "career_stage": spec["career_stage"],
        "institution": str(raw.get("institution") or "Research Institute").strip(),
        "education": str(raw.get("education") or "").strip(),
        "experience": str(raw.get("experience") or "").strip(),
        "bio": str(raw.get("bio") or "").strip(),
        "looking_for": str(raw.get("looking_for") or "").strip(),
        "interests": interests,
        "skills": skills,
        "offers": offers,
        "needs": needs,
        "contributable_skills": contributable,
        "want_to_learn": want_to_learn,
        "seeking_mentor": seeking,
        "open_to_mentoring": open_to,
        "methods_suggested": spec["methods_effective"],
        "methods_override": None,
        "methods_effective": spec["methods_effective"],
        "methods_reason": "Synthetic profile: methods label set by the seed spec",
        "is_synthetic": True,
        "is_complete": True,
    }


# Curated demo profiles for seeds 1 to 6
CURATED_DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "seed-001": {
        "full_name": "Dr. Amina Diallo",
        "institution": "Institute of Global Public Health",
        "education": "PhD in Public Health, Dakar Institute of Health Sciences",
        "experience": "Seven years conducting ethnographic and qualitative fieldwork in rural maternity clinics and urban health posts.",
        "bio": "Investigating how systemic administrative and economic barriers shape prenatal clinic attendance among marginalized populations.",
        "looking_for": "Seeking quantitative biostatisticians and epidemiologists to pair qualitative interview insights with spatial catchment modeling.",
        "interests": ["Maternal health access", "Community healthcare barriers", "Qualitative health systems", "Patient ethnography"],
        "skills": ["In-depth interviewing", "Thematic analysis", "Participant observation", "Community participatory research"],
        "offers": [],
        "needs": [],
        "contributable_skills": ["Qualitative fieldwork protocol design", "Contextual patient interview analysis"],
        "want_to_learn": ["Bayesian spatial epidemiology models", "Integration of qualitative findings with GIS"],
    },
    "seed-002": {
        "full_name": "Dr. Matteo Rossi",
        "institution": "Alpine Centre for Epidemiological Modeling",
        "education": "PhD in Biostatistics, University of Milan",
        "experience": "Five years developing spatial Bayesian models and longitudinal survival frameworks for infectious and non-communicable diseases.",
        "bio": "Modeling geographic disparities in healthcare access and survival outcomes using high-resolution spatial datasets.",
        "looking_for": "Collaborating with qualitative researchers to contextualize statistical catchment anomalies and ground truth model assumptions.",
        "interests": ["Spatial epidemiology", "Survival analysis", "Bayesian disease mapping", "Clinic accessibility modeling"],
        "skills": ["R / Stan", "Bayesian hierarchical modeling", "Spatial GIS analysis", "Survival analysis"],
        "offers": ["Guidance on spatial epidemiology modeling", "Statistical code review in R and Stan"],
        "needs": ["Qualitative context explaining clinic avoidance patterns", "Community health survey design advice"],
        "contributable_skills": [],
        "want_to_learn": [],
    },
    "seed-003": {
        "full_name": "Prof. Rajesh Patel",
        "institution": "Institute for Advanced Computing",
        "education": "PhD in Computer Science, Indian Institute of Science",
        "experience": "Over twelve years researching efficient transformer architectures, neural compression, and empirical benchmark evaluation.",
        "bio": "Leading a research lab focused on resource-efficient foundation models and transparent empirical evaluation standards.",
        "looking_for": "Mentoring motivated graduate students on deep learning efficiency while exploring rigorous hardware benchmarking pipelines.",
        "interests": ["Efficient deep learning", "Transformer architectures", "Empirical benchmarking", "Model compression"],
        "skills": ["PyTorch", "Model quantization", "Experimental benchmarking", "Grant proposal writing"],
        "offers": ["Research formulation and dissertation guidance", "Grant proposal review and career mentoring"],
        "needs": ["Assistance with open-source dataset benchmarking", "PyTorch performance profiling pipelines"],
        "contributable_skills": [],
        "want_to_learn": [],
    },
    "seed-004": {
        "full_name": "Jin-Woo Park",
        "institution": "Institute for Advanced Computing",
        "education": "B.S. in Computer Science; current M.S. candidate in Informatics",
        "experience": "Two years building distributed data ingestion pipelines and benchmarking neural network inference latencies.",
        "bio": "Master's researcher passionate about reproducible deep learning evaluation and high-throughput data curation.",
        "looking_for": "Seeking mentorship from senior faculty on framing empirical research questions and preparing publication manuscripts.",
        "interests": ["Deep learning benchmarking", "Transformer optimization", "Data pipelines", "GPU inference profiling"],
        "skills": ["PyTorch", "Python", "Hugging Face", "CUDA profiling", "Docker"],
        "offers": [],
        "needs": [],
        "contributable_skills": ["High-throughput PyTorch dataset curation", "GPU latency benchmarking pipelines"],
        "want_to_learn": ["Research question formulation", "Academic grant and paper writing"],
    },
    "seed-005": {
        "full_name": "Jordan Miller",
        "institution": "Horizon Collaborative Technologies Lab",
        "education": "M.S. in Human-Computer Interaction, University of Washington",
        "experience": "Six years as a quantitative user experience researcher designing large-scale telemetry experiments for workplace collaboration tools.",
        "bio": "Analyzing massive clickstream and telemetry datasets to quantify interaction patterns and team collaboration friction.",
        "looking_for": "Partnering with qualitative HCI researchers to discover the behavioral reasons behind telemetry drop-off trends.",
        "interests": ["Telemetry analysis", "A/B testing", "User engagement metrics", "Collaborative software ergonomics"],
        "skills": ["Clickstream log analysis", "Causal inference", "Python / Pandas", "Experimental design"],
        "offers": ["Industry career mentorship", "Quantitative telemetry analysis and experiment design review"],
        "needs": ["Qualitative methods for uninstrumented user behaviors", "Participatory workshop frameworks"],
        "contributable_skills": [],
        "want_to_learn": [],
    },
    "seed-006": {
        "full_name": "Astrid Berg",
        "institution": "Nordic University of Design & Technology",
        "education": "PhD Candidate in Interaction Design",
        "experience": "Four years conducting participatory design workshops, diary studies, and contextual inquiries into hybrid work fatigue.",
        "bio": "Investigating how remote knowledge workers experience notification overload and communicative friction in digital workspaces.",
        "looking_for": "Seeking collaboration with quantitative telemetry analysts to triangulate qualitative friction themes with product usage logs.",
        "interests": ["Participatory design", "Digital work fatigue", "Contextual inquiry", "Qualitative HCI"],
        "skills": ["Contextual inquiry", "Diary studies", "Qualitative thematic coding", "Co-design facilitation"],
        "offers": [],
        "needs": [],
        "contributable_skills": ["Contextual inquiry protocol design", "Qualitative co-design workshop facilitation"],
        "want_to_learn": ["Quantitative telemetry metric design", "Mixed-methods triangulation strategies"],
    },
}

REGIONAL_NAMES = {
    "East Asian": ["Wei Zhang", "Mei-Ling Zhou", "Hiroshi Tanaka", "Yuki Takahashi", "Chen Wei", "Soo-Jin Kim", "Kenji Sato"],
    "South Asian": ["Ananya Sharma", "Priya Iyer", "Rohan Mukherjee", "Kavita Rao", "Aditya Sen", "Sunita Nair", "Vikram Das"],
    "European (Germanic/Nordic)": ["Henrik Lindqvist", "Freja Nielsen", "Lukas Weber", "Astrid Berg", "Jonas Schmidt", "Elsa Larsson"],
    "European (Romance)": ["Clara Morales", "Hugo Dupont", "Elena Silva", "Camille Laurent", "Lucas Ferreira", "Sofia Rossi"],
    "European (Slavic)": ["Daria Ivanova", "Andrei Popescu", "Milena Novak", "Stanislav Kowalski", "Olga Petrova", "Tomasz Wisniewski"],
    "Middle Eastern": ["Tariq Al-Mansoor", "Leila Farhadi", "Rami Haddad", "Zeina Kassam", "Omar Kattan", "Farah Yousef"],
    "Latin American": ["Sofia Alvarez", "Diego Ramirez", "Camila Santos", "Lucas Hernandez", "Mariana Gomez", "Gabriel Castillo"],
    "Sub-Saharan African": ["Kwesi Mensah", "Chidimma Okoro", "Tendai Moyo", "Amina Diallo", "Ousmane Kane", "Zola Ndlovu"],
    "North American": ["Marcus Vance", "Eleanor Hayes", "Jordan Miller", "Rachel Brooks", "Ethan Sullivan", "Chloe Bennett"],
    "Southeast Asian": ["Linh Nguyen", "Somchai Prasert", "Siti Nurhaliza", "Bayu Pratama", "Thao Tran", "Rithy Meas"],
}

FICTIONAL_INSTITUTIONS = [
    "Institute for Advanced Informatics",
    "Boreal University of Science",
    "Crestview Institute of Technology",
    "Aurora University",
    "Pacific Horizon Polytechnic",
    "Meridian University of Applied Sciences",
    "Solaria Research Institute",
    "Valle Verde Institute of Science",
    "Savanna Polytechnic Institute",
    "Highland College of Research",
    "Cascade Institute for Advanced Study",
    "Archipelago Science Center",
]


def generate_offline_seed_profile(spec: dict[str, Any]) -> dict[str, Any]:
    """Generate a rich, deterministic synthetic profile matching the specification without network calls."""
    seed_id = spec["seed_id"]
    if seed_id in CURATED_DEMO_PROFILES:
        raw = dict(CURATED_DEMO_PROFILES[seed_id])
        cleaned = clean_seed_profile(raw, spec)
        if cleaned is not None:
            return cleaned

    num = int(seed_id.split("-")[1])
    region = spec.get("region", "North American")
    names_pool = REGIONAL_NAMES.get(region, REGIONAL_NAMES["North American"])
    name = names_pool[num % len(names_pool)]
    stage = spec["career_stage"]
    if stage in ("Faculty", "Postdoc"):
        prefix = "Prof. " if stage == "Faculty" else "Dr. "
        name = prefix + name

    inst = FICTIONAL_INSTITUTIONS[num % len(FICTIONAL_INSTITUTIONS)]
    field = spec["field"]
    methods = spec["methods_effective"]
    subfield = spec.get("subfield", f"Research in {field}")

    # Domain specific skills & interests
    interests = [
        f"{field.split('&')[0].strip()} foundations",
        subfield.capitalize() if len(subfield) < 35 else subfield[:35],
        f"{methods.title()} methodologies in {field.split()[0]}",
    ]
    skills = [
        f"{methods.title()} data analysis",
        f"{field.split()[0]} research design",
        "Scientific manuscript preparation",
        "Peer collaboration",
    ]

    open_to = spec["open_to_mentoring"]
    seeking = spec["seeking_mentor"]

    offers = [f"Guidance on {methods} research design", f"Career mentoring for {stage.lower()} researchers"] if open_to else []
    needs = [f"Interdisciplinary perspectives in {field.split()[0]}", f"Methodological critique for {methods} projects"] if open_to else []
    contributable = [f"Hands-on {methods} data collection", f"Literature synthesis in {field.split()[0]}"] if seeking else []
    want_to_learn = [f"Advanced {methods} protocols", "Publication and grant strategy"] if seeking else []

    raw = {
        "full_name": name,
        "institution": inst,
        "education": f"{'PhD' if stage in ('Postdoc', 'Faculty') else 'Degree'} in {field}, {inst}",
        "experience": f"Active researcher in {field} specializing in {methods} approaches.",
        "bio": f"Investigating {subfield.lower()} to advance theoretical and practical understanding.",
        "looking_for": f"Seeking collaborations with peers exploring {methods} and mixed approaches in {field}.",
        "interests": interests,
        "skills": skills,
        "offers": offers,
        "needs": needs,
        "contributable_skills": contributable,
        "want_to_learn": want_to_learn,
    }

    cleaned = clean_seed_profile(raw, spec)
    assert cleaned is not None, f"Clean failed for {seed_id}"
    return cleaned

