from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "IncidentBoard API"
    environment: str = "local"
    # Shown in the UI header. Comes from the Helm ConfigMap, so a Git change is visible in the browser.
    banner: str = "All systems monitored"
    database_url: str = "postgresql+psycopg://incident:incident@localhost:5432/incidentboard"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
