import os
import asyncio
from google import genai
from google.genai import types

async def test():
    api_key = "AIzaSyByoB2kziN3q3a5lMeEOT1dWo4uS8CmWfY"
    client = genai.Client(api_key=api_key)
    m = "gemini-3-pro-preview"
    try:
        print(f"Testing {m}...")
        response = await client.aio.models.generate_content(
            model=m,
            contents="Hello",
        )
        print(f"Success with {m}: {response.text}")
    except Exception as e:
        print(f"Failed with {m}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
