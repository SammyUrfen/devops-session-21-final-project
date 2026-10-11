from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MazeHub API"
    environment: str = "local"
    # Shown in the UI header. Comes from the Helm ConfigMap, so a Git change is visible in the browser.
    banner: str = "Find your way out"
    database_url: str = "postgresql+psycopg://mazehub:mazehub@localhost:5432/mazehub"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
