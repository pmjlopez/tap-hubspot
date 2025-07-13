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
    for stream in ["contacts", "companies", "deals", "meetings", "calls", "quotes", "line_items", "notes", "tasks", "emails"]:
        requests_mock.get(
            f"https://api.hubapi.com/crm/v3/properties/{stream}",
            json={"results": [{"name": "propertyname", "type": "propertytype"}]},
        )

    # Mock GET endpoints for non-CRM streams
    streams1 = [
        r"https://api.hubapi.com/analytics/v2/views",
        "https://api.hubapi.com/email/public/v1/campaigns/by-id?limit=100&orderBy=created",
        "https://api.hubapi.com/marketing/v3/forms/?limit=100",
        "https://api.hubapi.com/crm/v3/owners?limit=100",
    ]
    for s in streams1:
        if "analytics/v2/views" in s:
            requests_mock.get(
                r"https://api.hubapi.com/analytics/v2/views",
                json=[{"id": "1", "updatedDate": "2018-08-07"}],
                complete_qs=False,
            )
        elif "email/public/v1/campaigns/by-id?limit=100&orderBy=created" in s:
            requests_mock.get(
                s,
                json=[{"id": "1", "updatedDate": "2018-08-07"}],
            )
            # Also mock the endpoint with just ?orderBy=created
            requests_mock.get(
                "https://api.hubapi.com/email/public/v1/campaigns/by-id?orderBy=created",
                json=[{"id": "1", "updatedDate": "2018-08-07"}],
                complete_qs=False,
            )
        else:
            requests_mock.get(
                s,
                json=[{"id": "1", "updatedDate": "2018-08-07"}],
            )

    # Mock POST search endpoints for CRM streams
    post_endpoints = [
        "https://api.hubapi.com/crm/v3/objects/companies/search",
        "https://api.hubapi.com/crm/v3/objects/contacts/search",
        "https://api.hubapi.com/crm/v3/objects/deals/search",
        "https://api.hubapi.com/crm/v3/objects/meetings/search",
        "https://api.hubapi.com/crm/v3/objects/calls/search",
        "https://api.hubapi.com/crm/v3/objects/quotes/search",
        "https://api.hubapi.com/crm/v3/objects/line_items/search",
        "https://api.hubapi.com/crm/v3/objects/notes/search",
        "https://api.hubapi.com/crm/v3/objects/tasks/search",
        "https://api.hubapi.com/crm/v3/objects/emails/search",
    ]
    for endpoint in post_endpoints:
        if endpoint.endswith("calls/search"):
            requests_mock.post(
                endpoint,
                json={"results": [{"id": "1", "updatedAt": "2018-08-07T00:00:00Z", "archived": True}]},
            )
        else:
            requests_mock.post(
                endpoint,
                json={"results": [{"id": "1", "updatedAt": "2018-08-07T00:00:00Z"}]},
            )
    # Also mock GET for calls and companies search endpoints to handle legacy/test code
    requests_mock.get(
        "https://api.hubapi.com/crm/v3/objects/calls/search",
        json={"results": [{"id": "1", "updatedAt": "2018-08-07T00:00:00Z", "archived": True}]},
        complete_qs=False,
    )
    requests_mock.get(
        "https://api.hubapi.com/crm/v3/objects/companies/search",
        json={"results": [{"id": "1", "updatedAt": "2018-08-07T00:00:00Z", "archived": True}]},
        complete_qs=False,
    )
    requests_mock.get(
        "https://api.hubapi.com/crm/v3/objects/contacts/search",
        json={"results": [{"id": "1", "updatedAt": "2018-08-07T00:00:00Z", "archived": True}]},
        complete_qs=False,
    )
    # Mock associations child stream endpoints
    requests_mock.get(
        "https://api.hubapi.com/crm/v4/objects/companies/1/associations/contacts",
        json={"results": []},
        complete_qs=False,
    )
    requests_mock.get(
        "https://api.hubapi.com/crm/v4/objects/companies/1/associations/deals",
        json={"results": []},
        complete_qs=False,
    )
    requests_mock.get(
        "https://api.hubapi.com/crm/v4/objects/contacts/1/associations/companies",
        json={"results": []},
        complete_qs=False,
    )
    requests_mock.get(
        "https://api.hubapi.com/crm/v4/objects/contacts/1/associations/deals",
        json={"results": []},
        complete_qs=False,
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

    requests_mock.get(
        "https://api.hubapi.com/events/v3/events/",
        json={"results": []},
        complete_qs=False,
    )


def test_search_endpoint_always_uses_post():
    """Test that all streams now use POST with search endpoints."""
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
    
    # All streams now use POST
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
    # Should include associations
    assert "associations" in payload


def test_search_endpoint_with_few_properties():
    """Test that streams use POST even with few properties."""
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
    
    # Should use POST regardless of property count
    assert stream.http_method == "POST"
    payload = stream.prepare_request_payload(context={"archived": False}, next_page_token=None)
    assert payload is not None
    # Properties should be in payload, not URL params
    assert "properties" in payload
    expected_properties = few_properties + ["hs_createdate", "hs_lastmodifieddate"]
    assert set(payload["properties"]) == set(expected_properties)
