import pytest
import boto3
from moto import mock_aws
import os

os.environ.setdefault("SSM_PARAM_NAME", "/platform/account/env")

from swisscom.lambda_functions.index import get_parameter, lambda_handler


@pytest.fixture
def ssm_setup():
    with mock_aws():
        ssm = boto3.client("ssm", region_name="us-east-1")
        os.environ["SSM_PARAM_NAME"] = "/platform/account/env"
        yield ssm


def test_development_values(ssm_setup):
    ssm_setup.put_parameter(
        Name="/platform/account/env",
        Value="development",
        Type="String",
    )

    result = get_parameter("/platform/account/env")

    assert result["Environment"] == "development"
    assert result["ReplicaCount"] == 1


def test_production_values(ssm_setup):
    ssm_setup.put_parameter(
        Name="/platform/account/env",
        Value="PRODuction ",
        Type="String",
    )

    result = get_parameter("/platform/account/env")

    assert result["Environment"] == "production"
    assert result["ReplicaCount"] == 2


def test_invalid_environment(ssm_setup):
    ssm_setup.put_parameter(
        Name="/platform/account/env",
        Value="sandbox",
        Type="String",
    )

    with pytest.raises(ValueError):
        get_parameter("/platform/account/env")


def test_lambda_handler_create_event(ssm_setup):
    ssm_setup.put_parameter(
        Name="/platform/account/env",
        Value="staging",
        Type="String",
    )

    response = lambda_handler({"RequestType": "Create"}, None)

    assert response["Data"]["Environment"] == "staging"
    assert response["Data"]["ReplicaCount"] == 2


def test_lambda_handler_delete_event(ssm_setup):
    response = lambda_handler({"RequestType": "Delete"}, None)

    data = response.get("Data", {})

    assert data.get("ReplicaCount", 0) == 0
    assert data.get("Environment", "") == ""
