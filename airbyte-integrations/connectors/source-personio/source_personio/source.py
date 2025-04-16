#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple, Union
from urllib.parse import urlparse
from airbyte_cdk.models import SyncMode
from datetime import datetime

import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from source_personio.auth import PersonioAuth


# Full refresh stream

class PersonioBaseStream(HttpStream, ABC):
    """
    Base class for Personio API streams.
    """
    url_base = "https://api.personio.de/v1/"
    limit = 200

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


class PersonioStream(PersonioBaseStream):
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


class PersonioSubStream(PersonioBaseStream):
    def __init__(self, name: str, path: str, parent_stream: Stream, **kwargs: Any) -> None:
        self._name = name
        self._path = path
        self._parent_stream = parent_stream
        super().__init__(**kwargs)

    def parse_response(self, response: requests.Response, stream_slice: Mapping[str, Any] = None, **kwargs) -> Iterable[Mapping]:
        response_data = response.json().get("data")
        parent_id = stream_slice.get("id") if stream_slice else None
        for data in response_data:
            data["parent_id"] = parent_id
            yield data

    @property
    def name(self) -> str:
        return self._name

    def path(
        self,
        *,
        stream_state: Optional[Mapping[str, Any]] = None,
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> str:
        try:
            return self._path.format(stream_slice=stream_slice)
        except Exception as e:
            raise e

    def stream_slices(self, stream_state: Mapping[str, Any] = None, **kwargs) -> Iterable[Optional[Mapping[str, any]]]:
        for _slice in self._parent_stream.stream_slices(sync_mode=SyncMode.full_refresh):
            for parent_record in self._parent_stream.read_records(sync_mode=SyncMode.full_refresh, stream_slice=_slice):
                yield parent_record


class Employees(PersonioStream):
    cursor_field = "last_modified_at"
    primary_key = "id"

    def path(self, **kwargs) -> str:
        return "company/employees"

    @property
    def use_cache(self) -> bool:
        return True


class AbsenceBalanceEmployees(PersonioSubStream):
    primary_key = "id"


class Attributes(PersonioStream):
    cursor_field = "last_modified_at"
    primary_key = "key"

    def path(self, **kwargs) -> str:
        return "company/employees/attributes"

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        Example attributes response:
        {
            'key': 'first_name',
            'label': 'First name',
            'type': 'standard',
            'universal_id': 'first_name'
        }
        :return an iterable containing each record in the response
        """
        response_data = response.json().get("data")
        for data in response_data:
            yield data


class Attendances(PersonioStream):
    cursor_field = "updated_at"
    primary_key = "id"
    offset = 0

    def path(self, **kwargs) -> str:
        return "company/attendances"
    
    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        stream_data = response.json().get("data")
        if len(stream_data) < self.limit:
            return
        self.offset += self.limit
        return {"offset": self.offset}

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        params = super().request_params(
            stream_state=stream_state,
            stream_slice=stream_slice,
            next_page_token=next_page_token,
        )
        params["start_date"] = "2019-01-01"
        params["end_date"] = datetime.today().strftime('%Y-%m-%d')
        params["limit"] = self.limit
        if next_page_token:
            params.update(**next_page_token)
        return params

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        Example attributes response:
        {
            'id': 1111111,
            'type': 'AttendancePeriod',
            'attributes': {
                'employee': 22222,
                'date': '2022-07-14',
                'start_time': '12:30',
                'end_time': '17:00'
            }
        }
        :return an iterable containing each record in the response
        """
        response_data = response.json().get("data")
        for data in response_data:
            response = {}
            response["id"] = data.get("id")
            response["type"] = data.get("type")
            attributes = data.get("attributes", {})
            for attribute, value in attributes.items():
                response[attribute] = value
            yield response


class Absences(PersonioStream):
    cursor_field = "updated_at"
    primary_key = "id"
    offset = 0

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        stream_data = response.json().get("data")
        if len(stream_data) < self.limit:
            return
        self.offset += self.limit
        return {"offset": self.offset}

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        params = super().request_params(
            stream_state=stream_state,
            stream_slice=stream_slice,
            next_page_token=next_page_token,
        )
        params["start_date"] = "2019-01-01"
        params["end_date"] = datetime.today().strftime('%Y-%m-%d')
        params["limit"] = self.limit
        params["X-Personio-App-ID"] = "AIRBYTE"
        if next_page_token:
            params.update(**next_page_token)
        return params

    def path(self, **kwargs) -> str:
        return "company/time-offs"

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        Example attributes response:
        {
            "type": "TimeOffPeriod",
            "attributes": {
                "id": 1,
                "time_off_type": {
                    "type": "TimeOffType",
                    "attributes": {
                        "id": 1,
                        "name": "Bezahlter Urlaub/Paid vacation",
                    }
                },
                "employee": {
                    "type": "Employee"
                },
                "created_at": "2020-08-28T14:38:55+02:00",
                "updated_at": "2023-05-10T18:51:44+02:00"
            }
        }
        :return an iterable containing each record in the response
        """
        response_data = response.json().get("data")
        for data in response_data:
            response = {}
            response["type"] = data.get("type")
            attributes = data.get("attributes", {})
            for attribute, value in attributes.items():
                response[attribute] = value
            yield response


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
        employees = Employees(authenticator=auth)
        return [
            Attributes(authenticator=auth),
            employees,
            Attendances(authenticator=auth),
            Absences(authenticator=auth),
            AbsenceBalanceEmployees(
                name="absence_balance_employees",
                authenticator=auth,
                parent_stream=employees,
                path="company/employees/{stream_slice[id]}/absences/balance"
            ),
        ]
