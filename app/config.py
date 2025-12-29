from pydantic_settings import BaseSettings
from typing import Optional
from sqlalchemy.exc import IntegrityError


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""  # This will be overridden by your .env file
    DB_NAME: str = "attendance_db"

    # JWT configuration
    SECRET_KEY: str = (
        "your-secret-key-change-this-in-production"  # Change this in production
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def DATABASE_URL(self) -> str:
        """Construct MySQL database URL for SQLAlchemy using mysql-connector."""
        # CHANGED: "pymysql" to "mysqlconnector"
        return f"mysql+mysqlconnector://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
