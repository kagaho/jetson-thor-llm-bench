"""Small reproducible prompts. Benchmark runs are sequential by design."""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

CODING_PROMPT = (
    "Write exactly one Python function to detect cycles in a directed graph. "
    "Include time complexity and one small example. Be concise."
)
NEEDLE = "SW-THOR-7391-ALPHA"


def case_quick() -> dict:
    return {
        "messages": [{"role": "user", "content": CODING_PROMPT}],
        "reasoning_effort": "low",
        "max_tokens": 1024,
        "temperature": 0.0,
    }


def case_reasoning(mode: str) -> dict:
    case = {
        "messages": [{"role": "user", "content": CODING_PROMPT}],
        "max_tokens": 1200,
        "temperature": 0.0,
    }
    if mode == "off":
        case["chat_template_kwargs"] = {"enable_thinking": False}
    else:
        case["reasoning_effort"] = mode
    return case


def case_context(approx_tokens: int) -> dict:
    if approx_tokens < 256:
        raise ValueError("Target approximate tokens must be >=256")
    # 4 chars/token is *only* a sizing heuristic, not an actual token count.
    # The response's usage.prompt_tokens provides the actual token count.
    char_target = approx_tokens * 4
    filler = []
    n = 0
    chars = 0
    while chars < char_target:
        line = (
            f"Log entry {n:06d}: radar stable, sensors normal, diagnostics green, "
            "temperature nominal, processing healthy.\n"
        )
        filler.append(line)
        chars += len(line)
        n += 1
    point = max(1, len(filler) // 4)
    filler.insert(point, f"AUTHENTIC DEVICE REFERENCE CODE: {NEEDLE}\n")
    prompt = (
        "This is a synthetic long-context retrieval test. Exactly one reference code "
        "appears in the following logs. Return ONLY that reference code, without explanations.\n\n"
        + "".join(filler)
    )
    return {
        "messages": [{"role": "user", "content": prompt}],
        "reasoning_effort": "low",
        "temperature": 0.0,
        "max_tokens": 256,
    }


def case_vision(image_path: str) -> dict:
    path = Path(image_path)
    if not path.is_file():
        raise ValueError("Image file does not exist")
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Image exceeds the 8 MiB safety limit")
    mime, _ = mimetypes.guess_type(path.name)
    if mime not in ("image/jpeg", "image/png", "image/webp"):
        raise ValueError("Use a .jpg, .png, or .webp image")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Describe the main objects in this image in one short sentence."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
        ]}],
        "reasoning_effort": "low",
        "temperature": 0.0,
        "max_tokens": 512,
    }


def case_prefix(approx_tokens: int, nonce: str) -> dict:
    """Identical synthetic prompts for cold-ish and repeat prefix-cache probes."""
    if not (1024 <= approx_tokens <= 32768):
        raise ValueError("Prefix target must be 1024..32768 approximate tokens")
    line = "Repository notes: module parsing, error handling, deterministic tests, and clean interfaces.\n"
    shared = f"Benchmark marker {nonce}\n" + line * max(1, (approx_tokens * 4) // len(line))
    return {
        "messages": [
            {"role": "system", "content": "Synthetic coding context; answer the user request concisely.\n" + shared},
            {"role": "user", "content": "List two design principles for this repository in one sentence."},
        ],
        "temperature": 0.0,
        "reasoning_effort": "low",
        "max_tokens": 256,
    }


def case_agent(approx_tokens: int, nonce: str, turn: str) -> dict:
    """Agent-like follow-up: stable repository instructions, changing task tail.

    This is a synthetic *shared-prefix* test, not an end-to-end agent or tool
    execution benchmark. Same fixed system context is reused for both turns.
    """
    if turn not in ("first", "followup"):
        raise ValueError("agent turn must be first or followup")
    if not 1024 <= approx_tokens <= 32768:
        raise ValueError("Agent prefix target must be 1024..32768 approximate tokens")
    line = "Repository spec: parser, typed results, safe errors, deterministic unit tests, and reviews.\n"
    shared = f"Synthetic repository snapshot {nonce}\n" + line * max(1, (approx_tokens * 4) // len(line))
    task = (
        "Summarize two design constraints in one sentence." if turn == "first" else
        "Suggest two tests for those design constraints in one sentence."
    )
    return {
        "messages": [
            {"role": "system", "content": "You are a coding assistant. Use the shared repository notes.\n" + shared},
            {"role": "user", "content": task},
        ],
        "temperature": 0.0,
        "reasoning_effort": "low",
        "max_tokens": 256,
    }
