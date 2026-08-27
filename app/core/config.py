from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    max_upload_mb: int = 25
    allowed_extensions: set[str] = {".pdf", ".docx"}
    clause_model_dir: str = "models/clause-extraction-baseline"
    document_classification_model_dir: str = "models/document-classification-baseline"
    cors_allow_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    courtlistener_api_token: str | None = None
    courtlistener_base_url: str = "https://www.courtlistener.com/api/rest/v4/"
    db_path: str = "legalintel.db"
    jwt_secret_key: str | None = None


settings = Settings()
