import asyncio

from ai.ollama_service import generate_ai_response


async def main():
    response = await generate_ai_response(
        system_prompt="You are a helpful AI tutor.",
        user_prompt="Explain Docker in very simple terms.",
    )

    print(response)


if __name__ == "__main__":
    asyncio.run(main())