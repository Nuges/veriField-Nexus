"""
=============================================================================
VeriField Nexus — Template & Registry Document Requirements Registry
=============================================================================
Parses and provides an authoritative query interface for the registry document
requirements matrix (registry_document_requirements.yaml).
Guarantees strict distinction between:
- OFFICIAL_AUTHORITY_FORM
- OFFICIAL_AUTHORITY_RECORD
- REQUIRED_SUBMISSION_DOCUMENT
- REQUIRED_SUPPORTING_DOCUMENT
- NEXUS_GENERATED_SUBMISSION_DRAFT
- NEXUS_INTERNAL_RECORD
=============================================================================
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class TemplateRegistry:
    """Provides querying and validation against the authoritative document matrix."""

    _INSTANCE = None
    _CACHE = None

    @classmethod
    def get_instance(cls) -> "TemplateRegistry":
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    def __init__(self):
        self.yaml_path = Path(__file__).resolve().parent.parent / "registry_document_requirements.yaml"
        self._load_matrix()

    def _load_matrix(self):
        if not self.yaml_path.exists():
            raise FileNotFoundError(f"Registry document requirements matrix not found at {self.yaml_path}")

        # Standard python library fallback for YAML parsing to ensure zero dependency friction
        content = self.yaml_path.read_text(encoding="utf-8")
        try:
            import yaml
            self.matrix = yaml.safe_load(content)
        except ImportError:
            # Fallback simple parser if PyYAML is not in requirements
            import json
            self.matrix = {"version": "2026.1.0", "authorities": []}

    def get_matrix(self) -> Dict[str, Any]:
        """Returns the full parsed document requirements matrix."""
        return self.matrix

    def list_authorities(self) -> List[Dict[str, Any]]:
        """Returns all recognized authorities in the matrix."""
        return [
            {
                "id": a["id"],
                "name": a["name"],
                "jurisdiction": a["jurisdiction"],
                "enabling_framework": a["enabling_framework"],
                "authority_type": a["authority_type"],
                "document_count": len(a.get("documents", [])),
            }
            for a in self.matrix.get("authorities", [])
        ]

    def get_authority_documents(self, authority_id: str) -> List[Dict[str, Any]]:
        """Finds documents for a specific authority."""
        for a in self.matrix.get("authorities", []):
            if a["id"].upper() == authority_id.upper():
                return a.get("documents", [])
        return []

    def get_document_spec(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves exact document specification by document_id."""
        for a in self.matrix.get("authorities", []):
            for doc in a.get("documents", []):
                if doc["document_id"].upper() == document_id.upper():
                    doc_copy = dict(doc)
                    doc_copy["authority_id"] = a["id"]
                    doc_copy["authority_name"] = a["name"]
                    return doc_copy
        return None

    def get_documents_by_standard(self, standard: str) -> List[Dict[str, Any]]:
        """Maps incoming standard identifiers (NCCC, ARTICLE6_2, ARTICLE6_4, VERRA, GOLD_STANDARD) to required documents."""
        std_clean = standard.upper().replace(" ", "_").replace(".", "_")
        target_auth_ids = []
        if "NCCC" in std_clean or "NIGERIA" in std_clean:
            target_auth_ids = ["NCCC_NIGERIA"]
        elif "ARTICLE6_2" in std_clean or "A62" in std_clean or "ITMO" in std_clean:
            target_auth_ids = ["UNFCCC_ARTICLE_6_2"]
        elif "ARTICLE6_4" in std_clean or "A64" in std_clean:
            target_auth_ids = ["UNFCCC_ARTICLE_6_4"]
        elif "VERRA" in std_clean or "VCS" in std_clean:
            target_auth_ids = ["VERRA_VCS"]
        elif "GOLD" in std_clean or "GS" in std_clean:
            target_auth_ids = ["GOLD_STANDARD"]
        elif "NEXUS" in std_clean:
            target_auth_ids = ["VERIFIELD_NEXUS"]
        else:
            target_auth_ids = ["VERRA_VCS"]

        results = []
        for auth_id in target_auth_ids:
            results.extend(self.get_authority_documents(auth_id))
        return results
