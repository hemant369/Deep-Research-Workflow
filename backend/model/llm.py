from langchain_ollama import ChatOllama
from core.config import settings

llm = ChatOllama(
    model=settings.ollama_model,
    temperature=0,
    num_ctx=settings.ollama_context_size,
    num_predict=settings.ollama_max_tokens,
)
