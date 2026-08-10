from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    max_upload_mb: int = 25
    allowed_extensions: set[str] = {".pdf", ".docx"}


settings = Settings()
