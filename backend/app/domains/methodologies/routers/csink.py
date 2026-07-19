from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

@router.get("/kilns", response_model=List[Dict])
async def get_kilns():
    return [
        {"id": "k1", "name": "Kon-Tiki Deep Cone", "type": "Flame Curtain", "efficiency": 0.25},
        {"id": "k2", "name": "Oregon Kiln", "type": "Flame Curtain", "efficiency": 0.22},
        {"id": "k3", "name": "Ring Kiln", "type": "Retort", "efficiency": 0.35}
    ]

@router.get("/biomass", response_model=List[Dict])
async def get_biomass():
    return [
        {"id": "b1", "name": "Maize Cobs", "carbon_content": 0.45, "moisture": 0.15},
        {"id": "b2", "name": "Coffee Husks", "carbon_content": 0.48, "moisture": 0.12},
        {"id": "b3", "name": "Wood Trimmings", "carbon_content": 0.50, "moisture": 0.20}
    ]

@router.get("/batches/{code}")
async def get_batch(code: str):
    return {
        "batch_code": code,
        "status": "active",
        "kiln_id": "k1",
        "biomass_id": "b1",
        "start_time": "2026-07-14T00:00:00Z"
    }


from pydantic import BaseModel

class ParameterUpdate(BaseModel):
    value: float

@router.patch("/parameters/{param_id}")
async def update_parameter(param_id: str, payload: ParameterUpdate):
    # In a real CIOS, this would validate and store the parameter update in DB
    return {"success": True, "param_id": param_id, "updated_value": payload.value}
