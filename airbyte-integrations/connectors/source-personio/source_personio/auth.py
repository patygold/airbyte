#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#

from typing import Any, Mapping

import requests
from airbyte_cdk.sources.streams.http.requests_native_auth import (
    TokenAuthenticator
)


class PersonioOAuth(TokenAuthenticator):
    def __init__(
        self,
        config,
        token_refresh_endpoint: str,
    ):
        self._config = config
        self._token_refresh_endpoint = token_refresh_endpoint
        self._client_secret = self.get_client_secret()
        self._client_id = self.get_client_id()
        super().__init__(
            ""
        )

    def get_token_refresh_endpoint(self) -> str:
        return self._token_refresh_endpoint

    def get_client_id(self) -> str:
        return self._config["client_id"]

    def get_client_secret(self) -> str:
        return self._config["client_secret"]

    def build_refresh_request_headers(self) -> Mapping[str, Any]:
        return {
            "Content-Type": "application/json",
        }

    def build_refresh_request_body(self) -> Mapping[str, Any]:
        return {
            "client_id": self.get_client_id(),
            "client_secret": self.get_client_secret(),
        }

    def get_refresh_token(self) -> Mapping[str, Any]:
        response = requests.request(
            method="POST",
            url=self.get_token_refresh_endpoint(),
            params=self.build_refresh_request_body(),
            headers=self.build_refresh_request_headers(),
        )
        response.raise_for_status()
        return response.json()["data"]["token"]

    @property
    def token(self) -> str:
        return f"{self._auth_method} {self.get_refresh_token()}"


class PersonioAuth:
    def __new__(cls, config: dict) -> PersonioOAuth:
        return PersonioOAuth(config, "https://api.personio.de/v1/auth/")
