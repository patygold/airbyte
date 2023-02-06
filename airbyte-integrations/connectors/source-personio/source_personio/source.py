#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from source_personio.auth import PersonioAuth


# Full refresh stream
class PersonioStream(HttpStream, ABC):
    url_base = "https://api.personio.de/v1/"

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        """
        Return None when not using pagination

        :param response: the most recent response from the API
        :return If there is another page in the result, a mapping (e.g: dict) containing information needed to query the next page in the response.
                If there are no more pages in the result, return None.
        """
        return None

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        """
        https://developer.personio.de/reference/include-our-headers-in-your-requests
        """
        return {
            "X-Personio-App-ID": "AIRBYTE"
        }

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        Example attributes response:
        "id": {
            "label": "ID",
            "value": 1,
            "type": "integer",
            "universal_id": "id"
        },
        "supervisor": {
            "label": "Supervisor",
            "value": {
              "type": "Employee",
              "attributes": {
                "id": {
                  "label": "ID",
                  "value": 1,
                  "type": "integer",
                  "universal_id": "id"
                }
              }
            },
            "type": "standard",
            "universal_id": "supervisor"
        }
        :return an iterable containing each record in the response
        """
        response_data = response.json().get("data")
        for data in response_data:
            attributes = data.get("attributes", {})
            response = {}
            for attribute, value in attributes.items():
                # Only retrieves values which are defined in the schema
                if attribute in self.get_json_schema().get("properties"):
                    response[attribute] = value.get("value")
                    if (
                        isinstance(response[attribute], dict)
                    ):
                        sub_attributes = response[attribute].get("attributes", {})
                        for sub_attribute, sub_value in sub_attributes.items():
                            if isinstance(sub_value, dict):
                                sub_attributes[sub_attribute] = sub_value.get("value")
                        response[attribute] = sub_attributes
            yield response


class Employees(PersonioStream):
    cursor_field = "updated_since"
    primary_key = "id"

    def path(self, **kwargs) -> str:
        return "company/employees"


# Source
class SourcePersonio(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        """
        Check connection to Personio API.

        :param config:  the user-input config object conforming to the connector's spec.yaml
        :param logger:  logger object
        :return Tuple[bool, any]: (True, None) if the input config can be used to connect to the API successfully, (False, error) otherwise.
        """
        try:
            _ = PersonioAuth(config)
            return True, None
        except Exception as e:
            return False, str(e)

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        Get stream from Personio API.

        :param config: A Mapping of the user input configuration as defined in the connector spec.
        """
        auth = PersonioAuth(config)
        return [Employees(authenticator=auth)]
