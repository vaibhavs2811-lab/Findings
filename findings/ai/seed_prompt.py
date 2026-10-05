"""Structured prompt and Pydantic schemas for synthetic researcher profile batch generation."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


class SeedProfileItem(BaseModel):
    """Pydantic representation of generated researcher details for a given seed spec."""

    seed_id: str = Field(description="The unique seed identifier from the specification, e.g. 'seed-001'")
    full_name: str = Field(description="Culturally authentic name matching the region, with appropriate academic title (e.g. Dr., Prof., or plain for students)")
    institution: str = Field(description="Fictional university or research laboratory name (do not use real institutions)")
    education: str = Field(description="Academic degree and field (e.g. 'PhD in Cognitive Science, Fictional University')")
    experience: str = Field(description="2-3 sentences summarizing research methodology and background")
    bio: str = Field(description="Concise 2-3 sentence personal research statement describing passions and current projects")
    looking_for: str = Field(description="1-2 sentences on what types of collaborators, co-authors, or discussions they seek")
    interests: list[str] = Field(description="3 to 5 specific research topics or subject areas")
    skills: list[str] = Field(description="3 to 5 technical, methodological, or domain skills")
    offers: list[str] = Field(default_factory=list, description="What this researcher can mentor or guide others in (empty if not open to mentoring)")
    needs: list[str] = Field(default_factory=list, description="What guidance or assistance this researcher needs (empty if not open to mentoring)")
    contributable_skills: list[str] = Field(default_factory=list, description="Skills this researcher brings to a collaborative project (empty if not seeking a mentor)")
    want_to_learn: list[str] = Field(default_factory=list, description="Skills or knowledge this researcher wishes to acquire (empty if not seeking a mentor)")


class SeedBatchResponse(BaseModel):
    """Container for batch of generated profiles."""

    profiles: list[SeedProfileItem]


SEED_SYSTEM_INSTRUCTION = """You are an academic researcher profile generator for a peer collaboration network called Findings.
Generate realistic, high-quality, fictional academic researcher profiles based strictly on the provided specifications.

CRITICAL RULES:
1. All researcher names, universities, lab groups, and institutions MUST BE FICTIONAL.
2. DO NOT include email addresses, phone numbers, website links, or URLs in any field. If an email or URL is needed, code will synthesize it.
3. Align all terminology, methods, and skills directly with the specified field, career stage, and methods orientation (qualitative, quantitative, or mixed).
4. Strictly respect the mentoring toggles:
   - If seeking_mentor is False, leave contributable_skills and want_to_learn as empty lists.
   - If open_to_mentoring is False, leave offers and needs as empty lists.
5. Return a structured JSON object containing the 'profiles' list.
"""


def build_seed_prompt(batch_specs: list[dict[str, Any]]) -> str:
    """Format prompt for a batch of profile specifications."""
    specs_json = json.dumps(batch_specs, indent=2)
    return (
        f"Generate rich, realistic, academic researcher profiles for each of the following {len(batch_specs)} specifications.\n\n"
        f"Specifications:\n{specs_json}\n\n"
        "Ensure each item in 'profiles' has the exact 'seed_id' specified in its input."
    )
