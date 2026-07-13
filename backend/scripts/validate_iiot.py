import asyncio
import uuid
import sys
from datetime import datetime, timezone
import json

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_factory
from app.domains.iiot.services.edge_sync import EdgeSyncManager

async def validate_iiot():
    print("Starting Stream 4 & 5 IIoT and Security Validation...")
    
    async with async_session_factory() as db:
        manager = EdgeSyncManager(db)
        
        device_id = uuid.uuid4()
        payload = [{"local_identifier": "temp", "value": 25.5}]
        
        print("1. Validating Duplicate Detection...")
        is_dup1 = await manager.detect_duplicate(device_id, payload)
        if is_dup1:
            print("FAILED: First packet was marked as duplicate.")
            sys.exit(1)
        
        is_dup2 = await manager.detect_duplicate(device_id, payload)
        if not is_dup2:
            print("FAILED: Exact same packet was NOT marked as duplicate.")
            sys.exit(1)
            
        print("Duplicate detection verified.")
        
        print("2. Validating Sequence Validation...")
        is_seq_valid = await manager.validate_sequence(device_id, 1)
        if not is_seq_valid:
            print("FAILED: Sequence validation failed.")
            sys.exit(1)
            
        print("Sequence validation verified.")
        
        print("3. Validating Offline Buffering & DLQ routing...")
        await manager.buffer_offline_payload(device_id, "mqtt", payload)
        await manager.route_to_dead_letter_queue(device_id, payload, "Test Error")
        print("Buffering & DLQ methods executed successfully.")

        print("IIoT & Edge validation passed.")
        return True

if __name__ == "__main__":
    asyncio.run(validate_iiot())
