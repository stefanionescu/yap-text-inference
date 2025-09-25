"""Persona composition and prompt building functionality."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from functools import lru_cache

from prompts import (
    ANSWER_TYPES,
    AVOID_BASE_PERSONALITY,
    EXTERNAL_CONTEXT,
    FEATURES,
    HAMMER_FORMAT_INSTRUCTION,
    HAMMER_TASK_INSTRUCTION,
    HOW_TO_CHATS,
    LANGUAGE,
    MAN_GENDER_INFO,
    PERSONALITIES,
    UNIQUE_FEATURES,
    USER_INFO,
    USER_PERSONAL_INFO,
    WOMAN_GENDER_INFO,
)


def compose_persona(
    style: str = "wholesome",
    assistant_gender: str = "woman",
    user_identity: str = "non-binary",
    now_str: Optional[str] = None,
) -> str:
    s = style if style in PERSONALITIES else "wholesome"
    gender = assistant_gender if assistant_gender in {"man", "woman"} else "woman"
    user_id = (
        user_identity if user_identity in {"man", "woman", "non-binary"} else "non-binary"
    )

    if gender == "man":
        gender_info = MAN_GENDER_INFO.get(s, MAN_GENDER_INFO.get("wholesome", ""))
    else:
        gender_info = WOMAN_GENDER_INFO.get(s, WOMAN_GENDER_INFO.get("wholesome", ""))

    persona_section = PERSONALITIES[s].format(gender_info=gender_info)
    how_to_chat = HOW_TO_CHATS[s]
    avoid_section = AVOID_BASE_PERSONALITY[s]
    unique_section = UNIQUE_FEATURES.get(s, "")
    features_section = FEATURES.format(answer_type=ANSWER_TYPES[s])
    language_section = LANGUAGE

    user_personal_info = USER_PERSONAL_INFO.get(user_id, "")
    user_info_section = USER_INFO.format(user_personal_info=user_personal_info)

    if now_str is None:
        now_str = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    external_context = EXTERNAL_CONTEXT.format(date_time=now_str)

    parts = [
        persona_section,
        how_to_chat,
        avoid_section,
        unique_section,
        language_section,
        features_section,
        user_info_section,
        external_context,
    ]
    return "\n\n".join(p.strip() for p in parts if p).strip()


def build_chat_prompt(persona_text: str, history_text: str, user_utt: str) -> str:
    return (
        f"<|persona|>\n{persona_text.strip()}\n"
        f"<|history|>\n{history_text.strip()}\n"
        f"<|user|>\n{user_utt.strip()}\n<|assistant|>\n"
    )


def build_hammer_prompt(user_utt: str) -> str:
    return (
        f"{HAMMER_TASK_INSTRUCTION.strip()}\n\n"
        f"{HAMMER_FORMAT_INSTRUCTION.strip()}\n\n"
        f"User message:\n{user_utt.strip()}\n"
    )



# ----------------- Prefix sharing helpers (static vs runtime) -----------------

def compose_persona_static(style: str, assistant_gender: str) -> str:
    s = style if style in PERSONALITIES else "wholesome"
    gender = assistant_gender if assistant_gender in {"man", "woman"} else "woman"

    if gender == "man":
        gender_info = MAN_GENDER_INFO.get(s, MAN_GENDER_INFO.get("wholesome", ""))
    else:
        gender_info = WOMAN_GENDER_INFO.get(s, WOMAN_GENDER_INFO.get("wholesome", ""))

    persona_section = PERSONALITIES[s].format(gender_info=gender_info)
    how_to_chat = HOW_TO_CHATS[s]
    avoid_section = AVOID_BASE_PERSONALITY[s]
    unique_section = UNIQUE_FEATURES.get(s, "")
    language_section = LANGUAGE
    features_section = FEATURES.format(answer_type=ANSWER_TYPES[s])

    parts = [
        persona_section,
        how_to_chat,
        avoid_section,
        unique_section,
        language_section,
        features_section,
    ]
    # IMPORTANT: no time / user info / external context here
    return "\n\n".join(p.strip() for p in parts if p).strip()


def compose_persona_runtime(user_identity: str, now_str: str) -> str:
    user_id = user_identity if user_identity in {"man", "woman", "non-binary"} else "non-binary"
    user_personal_info = USER_PERSONAL_INFO.get(user_id, "")
    user_info_section = USER_INFO.format(user_personal_info=user_personal_info)
    external_context = EXTERNAL_CONTEXT.format(date_time=now_str)
    return "\n\n".join([user_info_section.strip(), external_context.strip()])


@lru_cache(maxsize=64)
def get_static_prefix(style: str, gender: str) -> str:
    s = style if style in PERSONALITIES else "wholesome"
    g = gender if gender in {"man", "woman"} else "woman"
    return compose_persona_static(s, g)


def build_chat_prompt_with_prefix(static_prefix: str, runtime_text: str, history_text: str, user_utt: str) -> str:
    return (
        f"<|persona|>\n{static_prefix.strip()}\n"
        f"<|history|>\n{history_text.strip()}\n"
        f"<|runtime|>\n{runtime_text.strip()}\n"
        f"<|user|>\n{user_utt.strip()}\n<|assistant|>\n"
    )

