"""
=============================================================================
Unit Tests for AI Orchestrator Service & LLM Provider Strategy
=============================================================================
"""

import pytest
from app.domains.ai_orchestrator.service import AIOrchestratorService
from app.core.llm_provider import LLMProviderFactory, DeterministicLLMProvider, ExternalLLMProvider

def test_intent_detection():
    orchestrator = AIOrchestratorService(db=None)

    assert orchestrator._detect_intent("what are the risk levels for this project?") == "risk"
    assert orchestrator._detect_intent("show carbon credit emissions reduction") == "carbon"
    assert orchestrator._detect_intent("review vvb verification status") == "verification"
    assert orchestrator._detect_intent("check compliance and ndpa regulations") == "compliance"
    assert orchestrator._detect_intent("show executive summary and kpi overview") == "executive"
    assert orchestrator._detect_intent("check photo evidence and gps coordinates") == "evidence"
    assert orchestrator._detect_intent("tell me about project 102") == "project"


@pytest.mark.asyncio
async def test_natural_language_response_builder():
    orchestrator = AIOrchestratorService(db=None)

    insights = [
        {"message": "Project Alpha has 45 verified cookstove installations.", "confidence": 0.95},
        {"message": "Overall trust score is 92%.", "confidence": 0.98},
    ]
    recommendations = [
        {"action": "Deploy field agents to sector 4 for spot checks.", "priority": "HIGH"},
    ]

    response = await orchestrator._build_response_text(
        query="what is the status of project alpha?",
        insights=insights,
        recommendations=recommendations,
        source_module="ProjectIntelligence",
    )

    assert "VeriField Trust Engine" in response or "found:" in response
    assert "45 verified cookstove installations" in response
    assert "Deploy field agents to sector 4" in response
    assert "[HIGH]" in response


def test_role_action_mappings():
    orchestrator = AIOrchestratorService(db=None)

    vvb_actions = orchestrator._get_role_actions("VVB_AUDITOR", [])
    assert any("Spot Check" in a["recommended_action"] for a in vvb_actions)

    agent_actions = orchestrator._get_role_actions("FIELD_AGENT", [])
    assert any("Capture" in a["recommended_action"] for a in agent_actions)


@pytest.mark.asyncio
async def test_llm_provider_factory_deterministic_default():
    provider = LLMProviderFactory.get_provider("deterministic")
    assert isinstance(provider, DeterministicLLMProvider)

    res = await provider.generate_response(
        query="test query",
        context_insights=[{"message": "Local telemetry OK", "confidence": 0.99}],
        context_recommendations=[],
    )
    assert res["provider"] == "deterministic"
    assert res["external_llm_used"] is False
    assert "Local telemetry OK" in res["text"]


@pytest.mark.asyncio
async def test_llm_provider_factory_external_fallback():
    # Without an API key, get_provider falls back to DeterministicLLMProvider
    provider = LLMProviderFactory.get_provider("gemini")
    assert isinstance(provider, (DeterministicLLMProvider, ExternalLLMProvider))

    res = await provider.generate_response(
        query="test query",
        context_insights=[{"message": "Local telemetry OK", "confidence": 0.99}],
        context_recommendations=[],
    )
    assert "Local telemetry OK" in res["text"]
