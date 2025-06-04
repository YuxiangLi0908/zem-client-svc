import os


class AppConfig:
    def __init__(self) -> None:
        self.JWT_ALGO = "HS256"
        self.SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "test-secret-key")


app_config = AppConfig()
