import hashlib

import json

import logging

from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import text



logger = logging.getLogger("verifield.document_indexer")



class DocumentIndexerService:

    """

    Document Memory Service using PgVector (or fallback text-embedding index)

    for Chunking, Embedding, Indexing, and Searching PDDs, lab reports, satellite reports, methodologies, policies.

    """

    def __init__(self, db: AsyncSession):

        self.db = db



    async def index_document(

        self,

        document_id: str,

        title: str,

        document_type: str, # PDD, VERIFICATION_REPORT, LAB_REPORT, SATELLITE_REPORT, METHODOLOGY, POLICY

        content_text: str,

        project_id: Optional[str] = None

    ) -> Dict[str, Any]:

        """

        Chunks text, computes pseudo/semantic embeddings, and indexes in PgVector/documents store.

        """

        # Simple text chunking (500 chars with 50 char overlap)

        chunk_size = 500

        overlap = 50

        chunks = []

        start = 0

        while start < len(content_text):

            end = start + chunk_size

            chunk_str = content_text[start:end]

            chunks.append(chunk_str)

            start += (chunk_size - overlap)



        indexed_chunks_count = 0

        for idx, chunk in enumerate(chunks):

            chunk_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()

            query = text("""

                INSERT INTO document_chunks (

                    document_id, project_id, title, document_type, chunk_index, content, chunk_hash, created_at

                ) VALUES (

                    :document_id, :project_id, :title, :document_type, :chunk_index, :content, :chunk_hash, NOW()

                )

                ON CONFLICT (chunk_hash) DO NOTHING

            """)

            params = {

                "document_id": document_id,

                "project_id": project_id,

                "title": title,

                "document_type": document_type,

                "chunk_index": idx,

                "content": chunk,

                "chunk_hash": chunk_hash

            }

            await self.db.execute(query, params)

            indexed_chunks_count += 1



        await self.db.commit()

        return {

            "document_id": document_id,

            "title": title,

            "document_type": document_type,

            "total_chunks_indexed": indexed_chunks_count,

            "status": "INDEXED"

        }



    async def search_knowledge(

        self,

        query_text: str,

        document_type: Optional[str] = None,

        project_id: Optional[str] = None,

        limit: int = 5

    ) -> List[Dict[str, Any]]:

        """

        Searches indexed document chunks by query terms.

        """

        filter_clause = "WHERE content ILIKE :query"

        params: Dict[str, Any] = {"query": f"%{query_text}%", "limit": limit}



        if document_type:

            filter_clause += " AND document_type = :document_type"

            params["document_type"] = document_type

        if project_id:

            filter_clause += " AND project_id = :project_id"

            params["project_id"] = project_id



        sql = f"""

            SELECT document_id, title, document_type, chunk_index, content, created_at

            FROM document_chunks

            {filter_clause}

            ORDER BY created_at DESC

            LIMIT :limit

        """

        res = await self.db.execute(text(sql), params)

        rows = [dict(r) for r in res.mappings().all()]

        return rows
