import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"


class TokenManager:
    def __init__(self):
        self.client_id = os.getenv("OPENSKY_CLIENT_ID")
        self.client_secret = os.getenv("OPENSKY_CLIENT_SECRET")
        self._token = None
        self._expiration = None

    def get_token(self):
        if self._token and datetime.now() < self._expiration:
            return self._token
        reponse = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=30,
        )
        reponse.raise_for_status()
        donnees = reponse.json()
        self._token = donnees["access_token"]
        duree = donnees.get("expires_in", 1800)
        self._expiration = datetime.now() + timedelta(seconds=duree - 60)
        return self._token


if __name__ == "__main__":
    tm = TokenManager()
    jeton = tm.get_token()
    print("Jeton obtenu, longueur :", len(jeton))
