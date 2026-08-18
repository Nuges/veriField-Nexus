"""
=============================================================================
VeriField Nexus — PDD Intelligence & Structured Fact Extractor
=============================================================================
Extracts verifiable climate project facts from PDDs, monitoring reports, and specs.
Strictly separates EXTRACTED facts from UNRESOLVED fields. Never fabricates values.
=============================================================================
"""

import re
from typing import Any, Dict, List, Optional

KNOWN_METHODOLOGY_CODES = [
    # Cookstoves
    "AMS_II_G", "AMS-II.G", "AMS-II-G",
    "VM0006", "VMR0006",
    "GS_TPDDTEC", "TPDDTEC",
    "GS_MECD", "MECD",
    "VMR0050",
    # Hybrid Energy & Mini-grids
    "AMS_I_F", "AMS-I.F", "AMS-I-F",
    "CI_GRID_DISPLACEMENT",
    "MINIGRID_DIESEL_DISPLACEMENT",
    "ENERGY_DISPLACEMENT",
    "SHS_RENEWABLE_DISPLACEMENT",
    # Biochar
    "VM0044",
    "BIOCHAR_C_SINK", "EBC", "PURO",
    # EV Mobility
    "EV_DISPLACEMENT", "VM0038", "AMS-III.C"
]

SECTOR_KEYWORDS = {
    "COOKSTOVES": ["cookstove", "cooking", "charcoal", "firewood", "improved cookstove", "thermal efficiency"],
    "HYBRID_ENERGY": ["mini-grid", "minigrid", "solar home system", "diesel displacement", "captive solar", "photovoltaic"],
    "BIOCHAR": ["biochar", "pyrolysis", "biomass residue", "carbon sink", "soil amendment", "permanence"],
    "EV_MOBILITY": ["electric vehicle", "ev fleet", "charging station", "two-wheeler", "fossil fuel displacement"],
}


class PDDParserService:
    """Extracts structured climate metadata and invariants from document text."""

    @classmethod
    def extract_pdd_facts(cls, full_text: str, document_type: str = "PDD") -> Dict[str, Any]:
        """
        Parses document text into structured fields.
        Returns a dict of extracted facts vs unresolved fields.
        """
        text_lower = full_text.lower()
        extracted: Dict[str, Any] = {}

        # 1. Project Name / Title
        project_name = cls._extract_field(
            full_text,
            patterns=[
                r"(?:project\s+title|project\s+name|name\s+of\s+project)\s*[:\-]\s*([^\n\r]+)",
                r"(?:programme\s+of\s+activities\s+title|poa\s+title)\s*[:\-]\s*([^\n\r]+)",
            ],
            clean_fn=lambda s: s.strip().strip('"\'')
        )
        extracted["project_name"] = project_name

        # 2. Project Developer / Proponent
        proponent = cls._extract_field(
            full_text,
            patterns=[
                r"(?:project\s+proponent|project\s+developer|coordinating\s+entity|implementing\s+partner)\s*[:\-]\s*([^\n\r]+)",
                r"(?:organisation|organization)\s*[:\-]\s*([^\n\r]+)",
            ],
            clean_fn=lambda s: s.strip().strip('"\'')
        )
        extracted["proponent"] = proponent

        # 3. Country & Location
        country = cls._extract_field(
            full_text,
            patterns=[
                r"(?:host\s+country|country\s+of\s+implementation|project\s+country)\s*[:\-]\s*([^\n\r]+)",
                r"(?:country)\s*[:\-]\s*([A-Za-z\s]+?)(?:,|\n|\r|$)",
            ],
            clean_fn=lambda s: s.strip().split(",")[0].strip()
        )
        extracted["country"] = country

        # 4. Methodology Code
        methodology = cls._extract_methodology(full_text)
        extracted["methodology_code"] = methodology

        # 5. Inferred Sector
        sector = cls._extract_sector(text_lower, methodology.get("value"))
        extracted["sector_code"] = sector

        # 6. Declared Asset Count / Installation Target
        declared_assets = cls._extract_numeric_field(
            full_text,
            patterns=[
                r"(?:total\s+installations|target\s+households|number\s+of\s+stoves|installed\s+assets|total\s+units|distributed\s+stoves)\s*[:\-]?\s*([0-9,]+)",
                r"([0-9,]+)\s*(?:improved\s+cookstoves|biochar\s+kilns|solar\s+arrays|ev\s+chargers)",
            ]
        )
        extracted["declared_asset_count"] = declared_assets

        # 7. Estimated Reductions (tCO2e)
        est_reductions = cls._extract_numeric_field(
            full_text,
            patterns=[
                r"(?:estimated\s+annual\s+reductions|annual\s+emission\s+reductions|expected\s+reductions|annual\s+tco2e)\s*[:\-]?\s*([0-9,.]+)",
                r"([0-9,.]+)\s*(?:tco2e/year|tonnes\s+co2e|tco2e\s+per\s+year)",
            ]
        )
        extracted["estimated_annual_tco2e"] = est_reductions

        # 8. Crediting Period
        crediting_period = cls._extract_crediting_period(full_text)
        extracted["crediting_period"] = crediting_period

        # Summary Metrics
        facts_extracted_count = sum(
            1 for k, v in extracted.items() if isinstance(v, dict) and v.get("status") == "EXTRACTED"
        )

        return {
            "document_type": document_type,
            "fields": extracted,
            "facts_count": facts_extracted_count,
            "extraction_confidence": round(facts_extracted_count / len(extracted), 2),
        }

    @staticmethod
    def _extract_field(text: str, patterns: List[str], clean_fn=lambda s: s) -> Dict[str, Any]:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = clean_fn(match.group(1))
                if val and len(val) > 2 and len(val) < 200:
                    return {
                        "value": val,
                        "status": "EXTRACTED",
                        "matched_pattern": pattern,
                    }
        return {"value": None, "status": "UNRESOLVED"}

    @staticmethod
    def _extract_numeric_field(text: str, patterns: List[str]) -> Dict[str, Any]:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw = match.group(1).replace(",", "").strip()
                try:
                    num_val = float(raw)
                    return {
                        "value": int(num_val) if num_val.is_integer() else num_val,
                        "status": "EXTRACTED",
                        "matched_pattern": pattern,
                    }
                except ValueError:
                    continue
        return {"value": None, "status": "UNRESOLVED"}

    @staticmethod
    def _extract_methodology(text: str) -> Dict[str, Any]:
        for code in KNOWN_METHODOLOGY_CODES:
            # Word boundary regex
            pattern = rf"\b{re.escape(code)}\b"
            if re.search(pattern, text, re.IGNORECASE):
                # Standardize code representation
                std_code = code.replace("-", "_").replace(".", "_").upper()
                if std_code in ("AMS_II_G", "VM0006", "GS_TPDDTEC", "GS_MECD", "VMR0050"):
                    return {"value": std_code, "status": "EXTRACTED", "sector": "COOKSTOVES"}
                elif std_code in ("AMS_I_F", "CI_GRID_DISPLACEMENT", "MINIGRID_DIESEL_DISPLACEMENT", "ENERGY_DISPLACEMENT", "SHS_RENEWABLE_DISPLACEMENT"):
                    return {"value": std_code, "status": "EXTRACTED", "sector": "HYBRID_ENERGY"}
                elif std_code in ("VM0044", "BIOCHAR_C_SINK"):
                    return {"value": std_code, "status": "EXTRACTED", "sector": "BIOCHAR"}
                elif std_code in ("EV_DISPLACEMENT", "VM0038"):
                    return {"value": std_code, "status": "EXTRACTED", "sector": "EV_MOBILITY"}
                return {"value": std_code, "status": "EXTRACTED"}
        return {"value": None, "status": "UNRESOLVED"}

    @staticmethod
    def _extract_sector(text_lower: str, matched_methodology: Optional[str]) -> Dict[str, Any]:
        if matched_methodology:
            if any(k in matched_methodology for k in ["COOK", "II_G", "VM0006", "TPDDTEC", "MECD"]):
                return {"value": "COOKSTOVES", "status": "EXTRACTED", "source": "methodology"}
            if any(k in matched_methodology for k in ["GRID", "MINIGRID", "ENERGY", "AMS_I_F", "SHS"]):
                return {"value": "HYBRID_ENERGY", "status": "EXTRACTED", "source": "methodology"}
            if any(k in matched_methodology for k in ["BIOCHAR", "VM0044"]):
                return {"value": "BIOCHAR", "status": "EXTRACTED", "source": "methodology"}
            if any(k in matched_methodology for k in ["EV", "MOBILITY"]):
                return {"value": "EV_MOBILITY", "status": "EXTRACTED", "source": "methodology"}

        # Keyword frequency scoring
        scores = {}
        for sector, kws in SECTOR_KEYWORDS.items():
            count = sum(text_lower.count(kw) for kw in kws)
            if count > 0:
                scores[sector] = count

        if scores:
            top_sector = max(scores, key=scores.get)
            return {"value": top_sector, "status": "EXTRACTED", "source": "keyword_frequency"}

        return {"value": None, "status": "UNRESOLVED"}

    @staticmethod
    def _extract_crediting_period(text: str) -> Dict[str, Any]:
        match = re.search(r"(?:crediting\s+period|period\s+of\s+crediting)\s*[:\-]?\s*([0-9]{1,2}\s*(?:years|yrs)|[0-9]{4}\s*(?:to|-)\s*[0-9]{4})", text, re.IGNORECASE)
        if match:
            return {"value": match.group(1).strip(), "status": "EXTRACTED"}
        return {"value": None, "status": "UNRESOLVED"}
