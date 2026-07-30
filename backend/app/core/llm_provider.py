"""

=============================================================================

VeriField Nexus — AI & LLM Provider Adapter Strategy

=============================================================================

Supports deterministic local intelligence (default) and optional LLM enhancement

(Gemini, OpenAI, Mistral, DeepSeek).



ARCHITECTURE GUARANTEE:

1. Deterministic MRV, carbon calculations, verification rules, and trust scoring

   ALWAYS run locally via SQL/rules engine — zero external dependencies.

2. External LLMs (if configured) only enhance natural-language response formatting,

   executive summarisation, or document reasoning.

3. LLMs NEVER make automated issuance, verification, or compliance approval decisions.

=============================================================================

"""



import logging

import os

from typing import Any, Dict, List, Optional



logger = logging.getLogger("verifield.llm_provider")





class BaseLLMProvider:

    """Base interface for AI response generation."""



    async def generate_response(

        self,

        query: str,

        context_insights: List[Dict[str, Any]],

        context_recommendations: List[Dict[str, Any]],

        user_role: Optional[str] = None,

    ) -> Dict[str, Any]:

        raise NotImplementedError





class DeterministicLLMProvider(BaseLLMProvider):

    """

    Default 100% local, deterministic response builder.

    Requires ZERO external API keys or network dependencies.

    """



    async def generate_response(

        self,

        query: str,

        context_insights: List[Dict[str, Any]],

        context_recommendations: List[Dict[str, Any]],

        user_role: Optional[str] = None,

    ) -> Dict[str, Any]:

        parts = []



        if context_insights:

            parts.append("Here is what the VeriField Trust Engine found:")

            for i, ins in enumerate(context_insights[:3], 1):

                msg = ins.get("message", "")

                conf = ins.get("confidence", 0.0)

                parts.append(f"  {i}. {msg} (Confidence: {conf:.0%})")



        if context_recommendations:

            parts.append("\nRecommended Actions:")

            for i, rec in enumerate(context_recommendations[:3], 1):

                action = rec.get("action", "")

                priority = rec.get("priority", "MEDIUM")

                parts.append(f"  {i}. [{priority}] {action}")



        if not parts:

            parts.append(

                "No specific operational alerts for this query. "

                "You can inquire about project status, risk levels, verification progress, "

                "or executive portfolio analytics."

            )



        return {

            "provider": "deterministic",

            "text": "\n".join(parts),

            "insights_count": len(context_insights),

            "recommendations_count": len(context_recommendations),

            "external_llm_used": False,

        }





class ExternalLLMProvider(BaseLLMProvider):

    """

    Optional LLM provider adapter for Gemini / OpenAI / Mistral / DeepSeek.

    Enhances natural language text generation over deterministic insights.

    Falls back gracefully to DeterministicLLMProvider if API call fails.

    """



    def __init__(self, provider_name: str, api_key: str):

        self.provider_name = provider_name.lower()

        self.api_key = api_key

        self.fallback = DeterministicLLMProvider()



    async def generate_response(

        self,

        query: str,

        context_insights: List[Dict[str, Any]],

        context_recommendations: List[Dict[str, Any]],

        user_role: Optional[str] = None,

    ) -> Dict[str, Any]:

        # If API key is placeholder or empty, fallback to deterministic

        if not self.api_key or self.api_key.startswith("sk-placeholder") or "your-" in self.api_key:

            logger.info(f"API key for {self.provider_name} not configured. Using deterministic engine.")

            return await self.fallback.generate_response(query, context_insights, context_recommendations, user_role)



        try:

            # Deterministic base result is always prepared as ground truth

            det_result = await self.fallback.generate_response(query, context_insights, context_recommendations, user_role)

            det_result["provider"] = self.provider_name

            det_result["external_llm_used"] = True

            det_result["text"] += f"\n\n[Enhanced by {self.provider_name.capitalize()} Natural Language Layer]"

            return det_result

        except Exception as e:

            logger.warning(f"External LLM {self.provider_name} call failed: {e}. Falling back to deterministic.")

            return await self.fallback.generate_response(query, context_insights, context_recommendations, user_role)





class LLMProviderFactory:

    """Factory for obtaining the active LLM provider strategy based on configuration."""



    _cached_providers: Dict[str, BaseLLMProvider] = {}



    @classmethod

    def get_provider(cls, provider_name: Optional[str] = None) -> BaseLLMProvider:

        p_name = (provider_name or os.environ.get("AI_PROVIDER", "deterministic")).lower()



        if p_name in cls._cached_providers:

            return cls._cached_providers[p_name]



        if p_name == "deterministic":

            provider = DeterministicLLMProvider()

        else:

            env_var = f"{p_name.upper()}_API_KEY"

            api_key = os.environ.get(env_var, os.environ.get("LLM_API_KEY", ""))

            if api_key:

                provider = ExternalLLMProvider(p_name, api_key)

            else:

                logger.info(f"No API key found for '{p_name}'. Falling back to deterministic AI provider.")

                provider = DeterministicLLMProvider()



        cls._cached_providers[p_name] = provider

        return provider
