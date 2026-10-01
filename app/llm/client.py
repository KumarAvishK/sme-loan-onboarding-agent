import os
from app.config import ANTHROPIC_API_KEY, CLAUDE_MODEL


def get_llm():
    if not ANTHROPIC_API_KEY:
        return None
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(model=CLAUDE_MODEL, temperature=0, max_tokens=1200)


def llm_text(system: str, user: str) -> str:
    llm = get_llm()
    if llm is None:
        return ""
    return llm.invoke([("system", system), ("human", user)]).content
