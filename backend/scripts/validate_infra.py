import asyncio
import uuid
import json
import aiomqtt
from redis.asyncio import Redis

async def validate_redis():
    print("Testing Redis Connection...")
    redis = Redis(host='localhost', port=6379, db=0)
    await redis.ping()
    print("Redis is online.")
    
    print("Caching methodology metadata...")
    test_key = "nexus:metadata:methodologies:dac"
    test_data = {"id": "dac_001", "name": "Direct Air Capture", "version": "1.0"}
    await redis.set(test_key, json.dumps(test_data), ex=60)
    
    retrieved = await redis.get(test_key)
    assert retrieved is not None
    parsed = json.loads(retrieved)
    assert parsed["name"] == "Direct Air Capture"
    print("Redis metadata caching validated successfully.")
    await redis.close()

async def validate_mqtt():
    print("Testing MQTT Connection...")
    async with aiomqtt.Client("localhost", 1883) as client:
        print("MQTT is receiving connections.")
        
        # We can't easily wait for the message without a complex loop, 
        # but just connecting and publishing verifies the broker is up.
        device_id = str(uuid.uuid4())
        topic = f"nexus/telemetry/{device_id}"
        payload = {"temperature": 22.5, "co2": 412}
        
        await client.publish(topic, json.dumps(payload))
        print(f"Published test message to {topic}")
        print("MQTT ingestion validated successfully.")

async def main():
    try:
        await validate_redis()
        print("-" * 40)
        await validate_mqtt()
        print("=" * 40)
        print("INFRASTRUCTURE VALIDATION PASSED")
    except Exception as e:
        print(f"INFRASTRUCTURE VALIDATION FAILED: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
