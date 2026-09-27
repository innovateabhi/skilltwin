import asyncio
import os
import subprocess
from typing import Any, Dict, List, Optional

import httpx


# ============================================================
# Ollama Configuration
# ============================================================

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://127.0.0.1:11434",
).rstrip("/")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen3:4b",
)


# ============================================================
# Ollama Process Management
# ============================================================

_ollama_start_lock = asyncio.Lock()
_ollama_process: Optional[subprocess.Popen] = None


# ============================================================
# Check whether Ollama is running
# ============================================================

async def is_ollama_running() -> bool:
    """
    Check whether the Ollama server is reachable.
    """

    try:
        async with httpx.AsyncClient(
            timeout=5.0
        ) as client:

            response = await client.get(
                f"{OLLAMA_BASE_URL}/api/tags"
            )

        return response.status_code == 200

    except Exception as exc:

        print(
            f"[Ollama] Server check failed: {exc}"
        )

        return False


# ============================================================
# Get installed Ollama models
# ============================================================

async def get_ollama_models() -> List[str]:
    """
    Return the names of all models installed in Ollama.
    """

    try:

        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:

            response = await client.get(
                f"{OLLAMA_BASE_URL}/api/tags"
            )

        response.raise_for_status()

        data = response.json()

        models = data.get(
            "models",
            []
        )

        if not isinstance(models, list):
            return []

        result: List[str] = []

        for model in models:

            if not isinstance(model, dict):
                continue

            name = model.get("name")

            if (
                isinstance(name, str)
                and name.strip()
            ):
                result.append(
                    name.strip()
                )

        return result

    except Exception as exc:

        print(
            "[Ollama] Unable to retrieve models: "
            f"{exc}"
        )

        return []


# ============================================================
# Ensure Ollama server is running
# ============================================================

async def ensure_ollama_running() -> bool:
    """
    Make sure the Ollama server is running.

    If Ollama is already running, nothing is started.

    If it is not running, attempt to start:
        ollama serve
    """

    global _ollama_process

    # --------------------------------------------------------
    # Ollama already running
    # --------------------------------------------------------

    if await is_ollama_running():
        return True

    # --------------------------------------------------------
    # Prevent multiple startup attempts
    # --------------------------------------------------------

    async with _ollama_start_lock:

        if await is_ollama_running():
            return True

        print(
            "[Ollama] Server is not running. "
            "Attempting to start Ollama..."
        )

        try:

            creation_flags = 0

            if os.name == "nt":
                creation_flags = (
                    subprocess.CREATE_NO_WINDOW
                )

            _ollama_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )

        except FileNotFoundError:

            print(
                "[Ollama] 'ollama' executable was not "
                "found in the system PATH."
            )

            return False

        except Exception as exc:

            print(
                "[Ollama] Unable to start Ollama: "
                f"{exc}"
            )

            return False

        # ----------------------------------------------------
        # Wait for Ollama
        # ----------------------------------------------------

        for attempt in range(30):

            await asyncio.sleep(0.5)

            if await is_ollama_running():

                print(
                    "[Ollama] Server started successfully."
                )

                return True

            print(
                "[Ollama] Waiting for server... "
                f"({attempt + 1}/30)"
            )

        print(
            "[Ollama] Server failed to become available."
        )

        return False


# ============================================================
# Ollama Status
# ============================================================

async def get_ollama_status() -> Dict[str, Any]:
    """
    Return current Ollama server and model status.
    """

    running = await is_ollama_running()

    models: List[str] = []

    if running:
        models = await get_ollama_models()

    return {
        "running": running,
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "model_available": OLLAMA_MODEL in models,
        "models": models,
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
    # Remove markdown fences
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
# Generate AI Response
# ============================================================

async def generate_ai_response(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Generate a response using Ollama.

    Important:
    - Qwen3 thinking is disabled.
    - Output token limit is large enough for JSON,
      resumes, interviews and ATS analysis.
    - Only final content is returned.
    """

    # --------------------------------------------------------
    # Make sure Ollama is running
    # --------------------------------------------------------

    ready = await ensure_ollama_running()

    if not ready:

        raise RuntimeError(
            "Ollama is not running and could not be started."
        )

    # --------------------------------------------------------
    # Verify model
    # --------------------------------------------------------

    models = await get_ollama_models()

    print(
        f"[Ollama] Available models: {models}"
    )

    print(
        f"[Ollama] Selected model: {OLLAMA_MODEL}"
    )

    if OLLAMA_MODEL not in models:

        raise RuntimeError(
            f"Ollama model '{OLLAMA_MODEL}' is not installed. "
            f"Available models: {models}"
        )

    # --------------------------------------------------------
    # Build request
    # --------------------------------------------------------

    payload = {
        "model": OLLAMA_MODEL,

        # We want one complete response.
        "stream": False,

        # ----------------------------------------------------
        # Qwen3 thinking
        # ----------------------------------------------------
        #
        # Disable thinking for application tasks where we
        # need a concise final response quickly.
        #
        "think": False,

        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        "options": {

            # Deterministic responses.
            "temperature": 0.2,

            "top_p": 0.8,

            # ------------------------------------------------
            # IMPORTANT FIX
            # ------------------------------------------------
            #
            # Previous value was only 100.
            #
            # That was causing:
            #
            # done_reason: length
            #
            # before Qwen finished its JSON.
            #
            "num_predict": 512,

            # Keep enough context for prompts containing
            # job descriptions and resume information.
            "num_ctx": 4096,
        },
    }

    print(
        "[Ollama] Sending generation request..."
    )

    # --------------------------------------------------------
    # Send request
    # --------------------------------------------------------

    try:

        timeout = httpx.Timeout(
            connect=10.0,
            read=300.0,
            write=30.0,
            pool=30.0,
        )

        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )

        # ----------------------------------------------------
        # HTTP error
        # ----------------------------------------------------

        if response.status_code >= 400:

            print(
                "[Ollama] HTTP error:"
            )

            print(
                f"Status: {response.status_code}"
            )

            print(
                f"Response: {response.text}"
            )

            response.raise_for_status()

        # ----------------------------------------------------
        # Parse response JSON
        # ----------------------------------------------------

        try:

            data = response.json()

        except Exception as exc:

            print(
                "[Ollama] Failed to parse JSON response."
            )

            print(
                f"Raw response: {response.text}"
            )

            raise RuntimeError(
                f"Ollama returned invalid JSON: {exc}"
            ) from exc

    except httpx.RequestError as exc:

        print(
            f"[Ollama] Network request failed: {exc}"
        )

        raise RuntimeError(
            "Could not connect to the Ollama server."
        ) from exc

    # --------------------------------------------------------
    # Debug metadata
    # --------------------------------------------------------

    print(
        "[Ollama] Response received."
    )

    print(
        "[Ollama] Model:",
        data.get("model")
    )

    print(
        "[Ollama] Done:",
        data.get("done")
    )

    print(
        "[Ollama] Done reason:",
        data.get("done_reason")
    )

    # --------------------------------------------------------
    # Message
    # --------------------------------------------------------

    message = data.get(
        "message"
    )

    if not isinstance(message, dict):

        raise RuntimeError(
            "Ollama response did not contain a valid "
            "'message' object."
        )

    # --------------------------------------------------------
    # Extract final content
    # --------------------------------------------------------

    content = message.get(
        "content",
        ""
    )

    thinking = message.get(
        "thinking",
        ""
    )

    if content is None:
        content = ""

    if thinking is None:
        thinking = ""

    if not isinstance(content, str):
        content = str(content)

    if not isinstance(thinking, str):
        thinking = str(thinking)

    content = clean_ai_response(
        content
    )

    # --------------------------------------------------------
    # Successful final response
    # --------------------------------------------------------

    if content:

        print(
            "[Ollama] Final response generated "
            f"({len(content)} characters)."
        )

        return content

    # --------------------------------------------------------
    # Thinking but no final response
    # --------------------------------------------------------

    if thinking:

        print(
            "[Ollama] WARNING: model generated "
            "thinking but no final content."
        )

        print(
            "[Ollama] Thinking length:",
            len(thinking)
        )

        raise RuntimeError(
            "The AI model generated reasoning but "
            "did not return a final answer."
        )

    # --------------------------------------------------------
    # Empty response
    # --------------------------------------------------------

    print(
        "[Ollama] Empty model response."
    )

    print(
        "[Ollama] done:",
        data.get("done")
    )

    print(
        "[Ollama] done_reason:",
        data.get("done_reason")
    )

    raise RuntimeError(
        "Ollama returned an empty response. "
        f"Model: {OLLAMA_MODEL}."
    )

