import asyncio
from google import genai

from app.config import settings


client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)


async def ask_ai(prompt: str):

    for attempt in range(3):

        try:
            response = await client.aio.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )

            return response.text

        except Exception as e:

            if "503" in str(e) or "UNAVAILABLE" in str(e):

                if attempt < 2:
                    await asyncio.sleep(3)
                    continue

            raise e