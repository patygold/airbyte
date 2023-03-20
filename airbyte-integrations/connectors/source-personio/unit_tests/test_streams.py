#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#

from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
import requests
from source_personio.source import PersonioStream, Employees


@pytest.fixture
def patch_base_class(mocker):
    mocker.patch.object(PersonioStream, "path", "company/employees")
    mocker.patch.object(PersonioStream, "primary_key", "id")
    mocker.patch.object(PersonioStream, "__abstractmethods__", set())


def test_request_params(patch_base_class):
    stream = PersonioStream()
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": None}
    expected_params = {"X-Personio-App-ID": "AIRBYTE"}

    assert stream.request_params(**inputs) == expected_params


def test_next_page_token(patch_base_class):
    stream = PersonioStream()
    inputs = {"response": MagicMock()}
    expected_token = None

    assert stream.next_page_token(**inputs) == expected_token


def test_parse_response(patch_base_class, fake_employees_response, fake_parsed_employees, requests_mock):
    stream = Employees()

    requests_mock.get('http://test.com', status_code=200, json=fake_employees_response)

    assert list(stream.parse_response(requests.get('http://test.com'))) == fake_parsed_employees


def test_request_headers(patch_base_class):
    stream = PersonioStream()
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": None}
    expected_headers = {}

    assert stream.request_headers(**inputs) == expected_headers


def test_http_method(patch_base_class):
    stream = PersonioStream()
    expected_method = "GET"

    assert stream.http_method == expected_method


@pytest.mark.parametrize(
    ("http_status", "should_retry"),
    [
        (HTTPStatus.OK, False),
        (HTTPStatus.BAD_REQUEST, False),
        (HTTPStatus.TOO_MANY_REQUESTS, True),
        (HTTPStatus.INTERNAL_SERVER_ERROR, True),
    ],
)
def test_should_retry(patch_base_class, http_status, should_retry):
    response_mock = MagicMock()
    response_mock.status_code = http_status
    stream = PersonioStream()

    assert stream.should_retry(response_mock) == should_retry


def test_backoff_time(patch_base_class):
    response_mock = MagicMock()
    stream = PersonioStream()
    expected_backoff_time = None

    assert stream.backoff_time(response_mock) == expected_backoff_time
