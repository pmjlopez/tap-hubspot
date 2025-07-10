"""Tests standard tap features using the built-in SDK tests library."""

import datetime
import pytest
from unittest.mock import Mock
from tap_hubspot.streams import ContactsStream

from singer_sdk.testing import get_standard_tap_tests

from tap_hubspot.tap import TapHubspot

SAMPLE_CONFIG = {
    "access_token": "accesstoken",
    "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
}


# Run standard built-in tap tests from the SDK:
def test_standard_tap_tests(requests_mock):
    """Run standard tap tests from the SDK."""
    for stream in ["contacts", "companies", "deals", "meetings"]:
        requests_mock.get(
            f"https://api.hubapi.com/crm/v3/properties/{stream}",
            json={"results": [{"name": "propertyname", "type": "propertytype"}]},
        )

    streams1 = [
        "https://api.hubapi.com/analytics/v2/views?limit=100",
        "https://api.hubapi.com/email/public/v1/campaigns/by-id?limit=100&orderBy=created",
        "https://api.hubapi.com/crm/v3/objects/companies?limit=100&properties=propertyname&archived=True",
        "https://api.hubapi.com/crm/v3/objects/companies?limit=100&properties=propertyname&archived=False",
        "https://api.hubapi.com/crm/v3/objects/contacts?limit=100&properties=propertyname&archived=True",
        "https://api.hubapi.com/crm/v3/objects/contacts?limit=100&properties=propertyname&archived=False",
        "https://api.hubapi.com/crm/v3/objects/deals?limit=100&properties=propertyname&archived=True",
        "https://api.hubapi.com/crm/v3/objects/deals?limit=100&properties=propertyname&archived=False",
        "https://api.hubapi.com/marketing/v3/forms/?limit=100",
        "https://api.hubapi.com/crm/v3/objects/meetings?limit=100&properties=propertyname",
        "https://api.hubapi.com/crm/v3/owners?limit=100",
    ]
    for s in streams1:
        requests_mock.get(
            s,
            json=[{"id": "1", "updatedDate": "2018-08-07"}],
        )

    streams2 = [
        "https://api.hubapi.com/marketing-emails/v1/emails/with-statistics?limit=100&offset=100&orderBy=created",
        "https://api.hubapi.com/automation/v3/workflows?limit=100",
        "https://api.hubapi.com/marketing/v3/forms/?count=100&formTypes=all",
        "https://api.hubapi.com/contacts/v1/lists?limit=100&count=100&offset=0",
    ]
    for s in streams2:
        requests_mock.get(
            s,
            json={
                "total": 1,
                "objects": [{"updated": 1553538703608}],
                "workflows": [{"updatedAt": 1467737836223}],
            },
        )
    tests = get_standard_tap_tests(TapHubspot, config=SAMPLE_CONFIG)
    for test in tests:
        test()


def test_post_method_triggered_for_many_properties():
    # Simulate a config with many properties
    many_properties = [f"field_{i}" for i in range(60)]
    config = {
        "access_token": "dummy",
        "selected_properties": {"contacts": many_properties},
        "start_date": "2023-01-01T00:00:00Z"
    }
    mock_tap = Mock()
    mock_tap.config = config
    mock_tap.logger = Mock()
    mock_tap.name = "tap-hubspot"
    stream = ContactsStream(tap=mock_tap)
    stream.logger = Mock()
    stream.name = "contacts"
    
    # Should use POST
    assert stream._should_use_post_method() is True
    assert stream.http_method == "POST"
    payload = stream.prepare_request_payload(context={"archived": False}, next_page_token=None)
    assert payload is not None
    assert "properties" in payload
    # Should include all fields plus the two date properties
    assert set(payload["properties"]) == set(many_properties + ["hs_createdate", "hs_lastmodifieddate"])
    assert payload["archived"] is False
    assert payload["limit"] == 100
    # Should include filter for incremental
    assert "filter" in payload


def test_get_method_for_few_properties():
    # Simulate a config with few properties
    few_properties = ["firstname", "lastname"]
    config = {
        "access_token": "dummy",
        "selected_properties": {"contacts": few_properties},
        "start_date": "2023-01-01T00:00:00Z"
    }
    mock_tap = Mock()
    mock_tap.config = config
    mock_tap.logger = Mock()
    mock_tap.name = "tap-hubspot"
    stream = ContactsStream(tap=mock_tap)
    stream.logger = Mock()
    stream.name = "contacts"
    
    # Should use GET
    assert stream._should_use_post_method() is False
    assert stream.http_method == "GET"
    payload = stream.prepare_request_payload(context={"archived": False}, next_page_token=None)
    assert payload is None
    # Properties should be in URL params and include the date properties
    params = stream.get_url_params(context={"archived": False}, next_page_token=None)
    expected_properties = few_properties + ["hs_createdate", "hs_lastmodifieddate"]
    assert set(params["properties"].split(",")) == set(expected_properties)
