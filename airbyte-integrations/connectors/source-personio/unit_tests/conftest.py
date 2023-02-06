#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


import pytest


@pytest.fixture
def fake_employees_response():
    return {
        "data": [
            {
                "attributes": {
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
                }
            }
        ]
    }


@pytest.fixture
def fake_parsed_employees():
    return [
        {
            "id": 1,
            "supervisor": {
                "id": 1
            }
        }
    ]
