import os
from dotenv import load_dotenv


class Config:
    OPENAI_API_KEY: str
    DEFAULT_ACCESS_TOKEN: str | None
    SF_DOMAIN: str | None

    def __init__(
            self, openai_api_key: str, sf_access_token: str,
            sf_domain: str | None) -> None:
        self.OPENAI_API_KEY = openai_api_key
        self.DEFAULT_ACCESS_TOKEN = sf_access_token
        self.SF_DOMAIN = sf_domain

    @classmethod
    def from_env(cls) -> 'Config':
        load_dotenv()

        return cls(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            sf_access_token=os.environ["DEFAULT_ACCESS_TOKEN"],
            sf_domain=os.environ.get("SF_DOMAIN", None)
        )
