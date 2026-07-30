from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional, Dict, Any, List

from pydantic import BaseModel



from app.db.session import get_db

from app.core.security import get_current_user

from app.domains.authentication.models import User

from app.domains.ai_orchestrator.service import AIOrchestratorService

from app.domains.ai_orchestrator.document_indexer import DocumentIndexerService

from app.domains.ai_orchestrator.memory import EnterpriseMemoryService



router = APIRouter()



class DocumentIndexRequest(BaseModel):

    document_id: str

    title: str

    document_type: str

    content_text: str

    project_id: Optional[str] = None



class MemoryDecisionRequest(BaseModel):

    user_id: str

    project_id: str

    recommendation_type: str

    recommendation_payload: Dict[str, Any]

    user_action: str

    impact_metrics: Optional[Dict[str, Any]] = None



class AIChatRequest(BaseModel):

    query: str

    context: Optional[Dict[str, Any]] = None



@router.post("/orchestrate")

async def run_ai_orchestrator(

    event_type: str = "MANUAL_TRIGGER",

    project_id: Optional[str] = None,

    user_role: Optional[str] = None,

    db: AsyncSession = Depends(get_db)

):

    service = AIOrchestratorService(db)

    return await service.orchestrate_analysis(event_type, project_id, user_role)



@router.post("/chat")

async def ai_chat(

    body: AIChatRequest,

    current_user: User = Depends(get_current_user),

    db: AsyncSession = Depends(get_db),

):

    """

    AI assistant chat endpoint. Accepts natural-language queries and routes

    to the appropriate intelligence module based on intent detection.

    """

    service = AIOrchestratorService(db)

    ctx = body.context or {}

    ctx.setdefault("user_id", str(current_user.id))

    result = await service.chat(

        query=body.query,

        user_role=current_user.role,

        context=ctx,

    )

    return result



@router.post("/documents/index")

async def index_document_content(

    data: DocumentIndexRequest,

    db: AsyncSession = Depends(get_db)

):

    indexer = DocumentIndexerService(db)

    return await indexer.index_document(

        document_id=data.document_id,

        title=data.title,

        document_type=data.document_type,

        content_text=data.content_text,

        project_id=data.project_id

    )



@router.get("/documents/search")

async def search_document_knowledge(

    q: str,

    document_type: Optional[str] = None,

    project_id: Optional[str] = None,

    limit: int = 5,

    db: AsyncSession = Depends(get_db)

):

    indexer = DocumentIndexerService(db)

    return await indexer.search_knowledge(q, document_type, project_id, limit)



@router.post("/memory/decisions")

async def record_decision_memory(

    data: MemoryDecisionRequest,

    db: AsyncSession = Depends(get_db)

):

    memory = EnterpriseMemoryService(db)

    return await memory.record_decision(

        user_id=data.user_id,

        project_id=data.project_id,

        recommendation_type=data.recommendation_type,

        recommendation_payload=data.recommendation_payload,

        user_action=data.user_action,

        impact_metrics=data.impact_metrics

    )



@router.get("/role-intelligence/{role}")

async def get_role_intelligence(

    role: str,

    project_id: Optional[str] = None,

    db: AsyncSession = Depends(get_db)

):

    service = AIOrchestratorService(db)

    res = await service.orchestrate_analysis("ROLE_REQUEST", project_id, role)

    return {

        "role": role,

        "insights": res["insights"],

        "recommendations": res["recommendations"],

        "actions": res["role_actions"]

    }
