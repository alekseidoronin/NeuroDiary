import os
import asyncio
from google import genai

async def list_models():
    api_key = "AIzaSyByoB2kziN3q3a5lMeEOT1dWo4uS8CmWfY"
    client = genai.Client(api_key=api_key)
    try:
        print("Available models:")
        for m in client.models.list():
            print(f"- {m.name}")
    except Exception as e:
        print(f"Failed to list models: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
