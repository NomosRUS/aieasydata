from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='OPENAI_')

    api_key: str = Field(..., min_length=1)
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"

class LocalLLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='LOCAL_LLM_')

    base_url: str = "http://ollama:11434"
    model: str = "aboba/saiga_mistral_13b"  # aboba/saiga_mistral_13b - отличная русская модель на базе Mistral
    api_key: str = "ollama"  # Required by openai client, but not used by ollama

class AppSettings(BaseSettings):
    openai: OpenAISettings = OpenAISettings()
    local_llm: LocalLLMSettings = LocalLLMSettings()

settings = AppSettings()
