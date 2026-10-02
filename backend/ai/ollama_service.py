import asyncio
import os
from typing import Any, Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================
# Environment Configuration
# ============================================================

load_dotenv()


# ============================================================
# Gemini Configuration
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
)


# ============================================================
# Gemini Client
# ============================================================

_gemini_client = None


def get_gemini_client():
    """
    Create and return a reusable Gemini client.
    """

    global _gemini_client

    if _gemini_client is not None:
        return _gemini_client

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Please add GEMINI_API_KEY to the backend .env file."
        )

    try:

        _gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        return _gemini_client

    except Exception as exc:

        print(
            f"[Gemini] Client initialization failed: {exc}"
        )

        raise RuntimeError(
            "Failed to initialize Gemini client."
        ) from exc


# ============================================================
# Gemini Status
# ============================================================

async def get_ollama_status() -> Dict[str, Any]:
    """
    Compatibility function.

    The existing AI Interview router still imports
    get_ollama_status(), so the function name is preserved.

    The actual provider is now Gemini.
    """

    configured = bool(
        GEMINI_API_KEY
        and GEMINI_API_KEY.strip()
    )

    return {
        "running": configured,
        "provider": "gemini",
        "model": GEMINI_MODEL,
        "model_available": configured,
        "base_url": "Google Gemini API",
    }


# ============================================================
# Clean AI Output
# ============================================================

def clean_ai_response(text: str) -> str:
    """
    Clean the final AI response.
    """

    if not isinstance(text, str):
        return ""

    text = text.strip()

    if not text:
        return ""

    # --------------------------------------------------------
    # Remove Markdown code fences
    # --------------------------------------------------------

    if text.startswith("```"):

        lines = text.splitlines()

        if len(lines) >= 2:
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip() == "```"
        ):
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # --------------------------------------------------------
    # Remove common prefixes
    # --------------------------------------------------------

    unwanted_prefixes = [
        "Final answer:",
        "Final Answer:",
        "Answer:",
        "Response:",
        "Question:",
        "Interview Question:",
    ]

    for prefix in unwanted_prefixes:

        if text.startswith(prefix):

            text = text[
                len(prefix):
            ].strip()

    return text.strip()


# ============================================================
# Internal Gemini Generation
# ============================================================

def _generate_with_gemini(
    client,
    system_prompt: str,
    user_prompt: str,
):
    """
    Synchronous Gemini generation function.

    This is executed inside asyncio.to_thread()
    so the FastAPI event loop is not blocked.
    """

    return client.models.generate_content(
        model=GEMINI_MODEL,

        contents=user_prompt,

        config=types.GenerateContentConfig(

            # Existing SkillTwin system prompts are passed
            # directly to Gemini.
            system_instruction=system_prompt,

            # Gemini 3.8 uses thinking_level instead of
            # the old thinking_budget configuration.
            #
            # LOW is appropriate for:
            # - AI Tutor
            # - Resume generation
            # - ATS analysis
            # - Interview questions
            #
            # It reduces unnecessary reasoning latency.
            thinking_config=types.ThinkingConfig(
                thinking_level="low"
            ),
        ),
    )


# ============================================================
# Generate AI Response
# ============================================================

async def generate_ai_response(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Generate an AI response using Google Gemini.

    This function intentionally keeps the same name and
    parameters as the old Ollama implementation.

    Existing routers therefore continue working:

        - ai_interview.py
        - ai_resume.py
        - ai_tutor.py
    """

    # --------------------------------------------------------
    # Validate prompts
    # --------------------------------------------------------

    if not isinstance(system_prompt, str):
        system_prompt = str(system_prompt)

    if not isinstance(user_prompt, str):
        user_prompt = str(user_prompt)

    system_prompt = system_prompt.strip()
    user_prompt = user_prompt.strip()

    if not user_prompt:

        raise RuntimeError(
            "Gemini request cannot contain an empty user prompt."
        )

    # --------------------------------------------------------
    # Get client
    # --------------------------------------------------------

    client = get_gemini_client()

    print(
        f"[Gemini] Selected model: {GEMINI_MODEL}"
    )

    print(
        "[Gemini] Sending generation request..."
    )

    # --------------------------------------------------------
    # Generate
    # --------------------------------------------------------

    try:

        response = await asyncio.to_thread(
            _generate_with_gemini,
            client,
            system_prompt,
            user_prompt,
        )

    except Exception as exc:

        print(
            "[Gemini] Generation request failed:"
        )

        print(
            str(exc)
        )

        raise RuntimeError(
            f"Gemini API request failed: {exc}"
        ) from exc

    # --------------------------------------------------------
    # Response received
    # --------------------------------------------------------

    print(
        "[Gemini] Response received."
    )

    # --------------------------------------------------------
    # Extract text
    # --------------------------------------------------------

    try:

        content = response.text

    except Exception as exc:

        print(
            "[Gemini] Unable to extract response text:"
        )

        print(
            str(exc)
        )

        raise RuntimeError(
            "Gemini returned a response but "
            "its text could not be extracted."
        ) from exc

    # --------------------------------------------------------
    # Normalize content
    # --------------------------------------------------------

    if content is None:
        content = ""

    if not isinstance(content, str):
        content = str(content)

    content = clean_ai_response(
        content
    )

    # --------------------------------------------------------
    # Successful response
    # --------------------------------------------------------

    if content:

        print(
            "[Gemini] Final response generated "
            f"({len(content)} characters)."
        )

        return content

    # --------------------------------------------------------
    # Empty response
    # --------------------------------------------------------

    print(
        "[Gemini] Empty model response."
    )

    raise RuntimeError(
        f"Gemini returned an empty response. "
        f"Model: {GEMINI_MODEL}."
    )
