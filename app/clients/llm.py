from langchain.chat_models import init_chat_model

from app.conf.config import settings

# 初始化聊天大模型实例
llm = init_chat_model(
    model=settings.llm_model,          # 指定模型名称
    model_provider='openai',           # 使用 OpenAI 兼容接口
    api_key=settings.llm_api_key,      # LLM 服务的密钥
    temperature=0.4,                   # 事实不跑偏，同时句子有自然变化
    base_url=settings.llm_base_url,    # 兼容 OpenAI 协议的接口服务
)