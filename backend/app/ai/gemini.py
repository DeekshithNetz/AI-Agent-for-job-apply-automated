import asyncio
from openai import AsyncOpenAI

from app.config import settings


client = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


async def ask_ai(prompt: str):

    for attempt in range(3):

        try:
            response = await client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return response.choices[0].message.content

        except Exception as e:

            if "503" in str(e) or "UNAVAILABLE" in str(e):

                if attempt < 2:
                    await asyncio.sleep(3)
                    continue

            raise e