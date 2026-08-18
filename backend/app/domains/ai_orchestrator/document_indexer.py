"""
=============================================================================
VeriField Nexus — Document Memory & Tenant-Scoped Indexer Service
=============================================================================
Provides chunking, SHA-256 hashing, and strict multi-tenant semantic indexing
across PDDs, monitoring reports, and climate methodology documents.
=============================================================================
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("verifield.document_indexer")


class DocumentIndexerService:
    """
    Document Memory Service with strict multi-tenant scoping and structured citations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def index_document(
        self,
        document_id: str,
        title: str,
        document_type: str,
        content_text: str,
        organization_id: Optional[UUID] = None,
        project_id: Optional[str] = None,
        sector_id: Optional[str] = None,
        methodology_id: Optional[str] = None,
        pages_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Chunks text with page boundaries, computes SHA-256 hashes,
        and indexes in document_chunks with strict tenant isolation.
        """
        chunks_to_insert: List[Dict[str, Any]] = []

        if pages_data and len(pages_data) > 0:
            for p in pages_data:
                p_num = p.get("page_number", 1)
                p_text = p.get("text", "")
                if not p_text:
                    continue

                # Chunk page content (500 chars with 50 overlap)
                chunk_size = 500
                overlap = 50
                start = 0
                idx = 0
                while start < len(p_text):
                    end = start + chunk_size
                    chunk_str = p_text[start:end]
                    chunk_hash = hashlib.sha256(f"{document_id}_{p_num}_{idx}_{chunk_str}".encode("utf-8")).hexdigest()
                    chunks_to_insert.append({
                        "document_id": document_id,
                        "organization_id": str(organization_id) if organization_id else None,
                        "project_id": str(project_id) if project_id else None,
                        "sector_id": str(sector_id) if sector_id else None,
                        "methodology_id": str(methodology_id) if methodology_id else None,
                        "title": title,
                        "document_type": document_type,
                        "page_number": p_num,
                        "section": p.get("section", "General"),
                        "chunk_index": idx,
                        "content": chunk_str,
                        "chunk_hash": chunk_hash,
                    })
                    idx += 1
                    start += (chunk_size - overlap)
        else:
            # Chunk generic text
            chunk_size = 500
            overlap = 50
            start = 0
            idx = 0
            while start < len(content_text):
                end = start + chunk_size
                chunk_str = content_text[start:end]
                chunk_hash = hashlib.sha256(f"{document_id}_1_{idx}_{chunk_str}".encode("utf-8")).hexdigest()
                chunks_to_insert.append({
                    "document_id": document_id,
                    "organization_id": str(organization_id) if organization_id else None,
                    "project_id": str(project_id) if project_id else None,
                    "sector_id": str(sector_id) if sector_id else None,
                    "methodology_id": str(methodology_id) if methodology_id else None,
                    "title": title,
                    "document_type": document_type,
                    "page_number": 1,
                    "section": "General",
                    "chunk_index": idx,
                    "content": chunk_str,
                    "chunk_hash": chunk_hash,
                })
                idx += 1
                start += (chunk_size - overlap)

        indexed_count = 0
        for item in chunks_to_insert:
            query = text("""
                INSERT INTO document_chunks (
                    document_id, organization_id, project_id, sector_id, methodology_id,
                    title, document_type, page_number, section, chunk_index, content, chunk_hash, created_at
                ) VALUES (
                    :document_id, :organization_id, :project_id, :sector_id, :methodology_id,
                    :title, :document_type, :page_number, :section, :chunk_index, :content, :chunk_hash, CURRENT_TIMESTAMP
                )
                ON CONFLICT (chunk_hash) DO NOTHING

            """)
            await self.db.execute(query, item)
            indexed_count += 1

        await self.db.flush()


        return {
            "document_id": document_id,
            "title": title,
            "document_type": document_type,
            "total_chunks_indexed": indexed_count,
            "status": "INDEXED",
        }

    async def search_knowledge(
        self,
        query_text: str,
        document_type: Optional[str] = None,
        project_id: Optional[str] = None,
        organization_id: Optional[UUID] = None,
        is_super_admin: bool = False,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Searches indexed document chunks with strict multi-tenant isolation.
        Non-super-admins can NEVER retrieve cross-tenant chunks.
        """
        filter_clauses = ["LOWER(content) LIKE LOWER(:query)"]
        params: Dict[str, Any] = {"query": f"%{query_text}%", "limit": limit}


        # Multi-Tenant Enforcement
        if not is_super_admin:
            if not organization_id:
                # Disallow unauthenticated / un-scoped tenant searches
                return []
            filter_clauses.append("organization_id = :organization_id")
            params["organization_id"] = str(organization_id)
        elif organization_id:
            # Super-admin optionally scoped to organization
            filter_clauses.append("organization_id = :organization_id")
            params["organization_id"] = str(organization_id)

        if document_type:
            filter_clauses.append("document_type = :document_type")
            params["document_type"] = document_type

        if project_id:
            filter_clauses.append("project_id = :project_id")
            params["project_id"] = str(project_id)

        where_sql = " AND ".join(filter_clauses)
        sql = f"""
            SELECT
                document_id, organization_id, project_id, sector_id, methodology_id,
                title, document_type, page_number, section, chunk_index, content, created_at
            FROM document_chunks
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit
        """

        res = await self.db.execute(text(sql), params)
        rows = []
        for r in res.mappings().all():
            d = dict(r)
            p_num = d.get("page_number") or 1
            sec = d.get("section") or "General"
            d["citation"] = f"Source: '{d.get('title')}' | Page {p_num} | Section {sec}"
            rows.append(d)

        return rows
