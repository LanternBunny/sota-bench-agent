import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3")
FAST_MODEL = os.getenv("FAST_MODEL", "deepseek-ai/DeepSeek-V3")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "Qwen/Qwen2.5-72B-Instruct")

MAX_SEARCH_LOOPS = 3
MAX_CODE_FIX_LOOPS = 5
BEST_OF_N = 3


def get_llm(model: str | None = None, temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        model=model or LLM_MODEL,
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL,
        temperature=temperature,
    )


def get_judge_llm() -> ChatOpenAI:
    return get_llm(model=JUDGE_MODEL, temperature=0.0)


def get_fast_llm(temperature: float = 0.7) -> ChatOpenAI:
    return get_llm(model=FAST_MODEL, temperature=temperature)
