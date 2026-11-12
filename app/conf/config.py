from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录下的 .env 文件
ENV_FILE = Path(__file__).parents[2] / '.env'


class Settings(BaseSettings):
    # LLM
    llm_api_key: str
    llm_model: str
    llm_base_url: str

    # 数据库
    database_url: str

    # 商城 API
    travel_api_base_url: str

    # 演示环境：对话未显式传 user_id 时使用
    demo_user_id: int = 10001

    # 服务器
    app_host: str
    app_port: int

    # 从 .env 读取配置
    model_config = SettingsConfigDict(env_file=ENV_FILE)


settings = Settings()