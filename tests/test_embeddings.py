"""Unit tests for findings/ai/embeddings.py."""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from findings.ai.client import AIUnavailable
from findings.ai.embeddings import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    EMBEDDING_PREFIX,
    embed_profile,
    mock_embedding,
    normalize_vector,
    profile_embedding_text,
    profile_hash,
)


def test_profile_embedding_text_content_and_prefix():
    profile = {
        "full_name": "Dr. Secret Name",
        "institution": "Prestige Ivy League University",
        "education": "PhD Harvard 2020",
        "email": "secret@prestige.edu",
        "career_stage": "Postdoc",
        "methods_effective": "quantitative",
        "interests": ["Neuroimaging", "fMRI"],
        "skills": ["Python", "PyTorch", "Signal processing"],
        "experience": "Three years post-doctoral experience in cortical mapping.",
        "looking_for": "Collaborators with MEG or EEG datasets.",
        "offers": ["Guidance on fMRI pre-processing"],
        "needs": ["MEG signal expertise"],
        "contributable_skills": ["High-resolution fMRI pipeline"],
        "want_to_learn": ["MEG dipole source localization"],
        "bio": "Passionate about decoding auditory representations.",
    }

    text = profile_embedding_text(profile)

    # 1. Prefix is present
    assert text.startswith(EMBEDDING_PREFIX)

    # 2. Domain content is present
    assert "Career stage: Postdoc" in text
    assert "Methods orientation: quantitative" in text
    assert "Research interests: Neuroimaging, fMRI" in text
    assert "Skills and methodologies: Python, PyTorch, Signal processing" in text
    assert "Research experience: Three years post-doctoral experience" in text
    assert "Looking for: Collaborators with MEG or EEG datasets." in text
    assert "Mentoring offers: Guidance on fMRI pre-processing" in text
    assert "Mentoring needs: MEG signal expertise" in text
    assert "Contributable skills: High-resolution fMRI pipeline" in text
    assert "Want to learn: MEG dipole source localization" in text
    assert "Bio: Passionate about decoding auditory representations." in text

    # 3. Bias-inducing identifiers are strictly excluded
    assert "Dr. Secret Name" not in text
    assert "Prestige Ivy League" not in text
    assert "Harvard" not in text
    assert "secret@prestige.edu" not in text


def test_normalize_vector_unit_length():
    # Regular vector
    raw = [3.0, 4.0]
    normed = normalize_vector(raw)
    assert normed == [0.6, 0.8]
    assert math.isclose(math.sqrt(sum(x * x for x in normed)), 1.0)

    # Zero vector
    zero = [0.0, 0.0, 0.0]
    assert normalize_vector(zero) == [0.0, 0.0, 0.0]


def test_profile_hash_deterministic_and_unique():
    text1 = "task: sentence similarity | query: Research on climate economics."
    text2 = "task: sentence similarity | query: Research on climate economics."
    text3 = "task: sentence similarity | query: Research on computational genomics."

    h1 = profile_hash(text1)
    h2 = profile_hash(text2)
    h3 = profile_hash(text3)

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # SHA256 hex digest


def test_mock_embedding_deterministic_768_dim():
    text = "Sample research profile text"
    v1 = mock_embedding(text)
    v2 = mock_embedding(text)

    assert len(v1) == EMBEDDING_DIM
    assert v1 == v2

    norm = math.sqrt(sum(x * x for x in v1))
    assert math.isclose(norm, 1.0, rel_tol=1e-5)


def test_embed_profile_calls_sdk_and_normalizes():
    mock_client = MagicMock()
    # Provide unnormalized vector of length 768
    raw_values = [2.0] * EMBEDDING_DIM
    mock_response = MagicMock()
    mock_response.embedding.values = raw_values
    mock_client.models.embed_content.return_value = mock_response

    vec = embed_profile("Test text", client=mock_client)

    assert len(vec) == EMBEDDING_DIM
    norm = math.sqrt(sum(x * x for x in vec))
    assert math.isclose(norm, 1.0, rel_tol=1e-5)

    mock_client.models.embed_content.assert_called_once()
    call_kwargs = mock_client.models.embed_content.call_args.kwargs
    assert call_kwargs["model"] == EMBEDDING_MODEL
    assert call_kwargs["contents"] == "Test text"
    assert call_kwargs["config"].output_dimensionality == EMBEDDING_DIM


def test_embed_profile_wraps_exceptions():
    mock_client = MagicMock()
    mock_client.models.embed_content.side_effect = RuntimeError("API Quota Exceeded")

    with pytest.raises(AIUnavailable, match="Embedding generation failed"):
        embed_profile("Test text", client=mock_client)
