"""Tests for date filtering functionality."""

import datetime
import pytest
from unittest.mock import Mock, patch

from tap_hubspot.client import HubspotStream
from tap_hubspot.streams import ContactsStream


class TestDateFiltering:
    """Test date filtering functionality."""

    def test_get_date_filter_params_with_string_date(self):
        """Test date filtering with string date format."""
        # Create a mock config with start_date
        config = {
            "access_token": "test_token",
            "start_date": "2023-01-01T00:00:00Z"
        }
        
        # Create a properly mocked tap
        mock_tap = Mock()
        mock_tap.config = config
        mock_tap.logger = Mock()
        mock_tap.name = "tap-hubspot"
        
        # Create a stream instance
        stream = ContactsStream(tap=mock_tap)
        stream.name = "contacts"
        stream.logger = Mock()
        
        # Test the date filter method
        filter_params = stream._get_date_filter_params()
        
        assert filter_params is not None
        assert "filter" in filter_params
        # Should contain both creation and modification date filters
        assert "hs_createdate>=" in filter_params["filter"]
        assert "hs_lastmodifieddate>=" in filter_params["filter"]
        assert "OR" in filter_params["filter"]

    def test_get_date_filter_params_with_datetime_object(self):
        """Test date filtering with datetime object."""
        # Create a mock config with datetime start_date
        start_date = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
        config = {
            "access_token": "test_token",
            "start_date": start_date
        }
        
        # Create a properly mocked tap
        mock_tap = Mock()
        mock_tap.config = config
        mock_tap.logger = Mock()
        mock_tap.name = "tap-hubspot"
        
        # Create a stream instance
        stream = ContactsStream(tap=mock_tap)
        stream.name = "contacts"
        stream.logger = Mock()
        
        # Test the date filter method
        filter_params = stream._get_date_filter_params()
        
        assert filter_params is not None
        assert "filter" in filter_params

    def test_get_date_filter_params_without_start_date(self):
        """Test date filtering when no start_date is provided."""
        config = {
            "access_token": "test_token"
            # No start_date
        }
        
        # Create a properly mocked tap
        mock_tap = Mock()
        mock_tap.config = config
        mock_tap.logger = Mock()
        mock_tap.name = "tap-hubspot"
        
        # Create a stream instance
        stream = ContactsStream(tap=mock_tap)
        stream.name = "contacts"
        stream.logger = Mock()
        
        # Test the date filter method
        filter_params = stream._get_date_filter_params()
        
        assert filter_params is None

    def test_get_url_params_includes_date_filter(self):
        """Test that get_url_params includes date filtering for incremental streams."""
        config = {
            "access_token": "test_token",
            "start_date": "2023-01-01T00:00:00Z"
        }
        
        # Create a properly mocked tap
        mock_tap = Mock()
        mock_tap.config = config
        mock_tap.logger = Mock()
        mock_tap.name = "tap-hubspot"
        
        # Create a stream instance
        stream = ContactsStream(tap=mock_tap)
        stream.name = "contacts"
        stream.logger = Mock()
        stream.replication_method = "INCREMENTAL"
        stream.replication_key = "updatedAt"
        
        # Test the URL params method
        params = stream.get_url_params(context={"archived": False}, next_page_token=None)
        
        assert "limit" in params
        assert "filter" in params
        assert "hs_createdate>=" in params["filter"]

    def test_get_url_params_no_date_filter_for_full_table(self):
        """Test that get_url_params doesn't include date filtering for full table streams."""
        config = {
            "access_token": "test_token",
            "start_date": "2023-01-01T00:00:00Z"
        }
        
        # Create a properly mocked tap
        mock_tap = Mock()
        mock_tap.config = config
        mock_tap.logger = Mock()
        mock_tap.name = "tap-hubspot"
        
        # Create a stream instance
        stream = ContactsStream(tap=mock_tap)
        stream.name = "contacts"
        stream.logger = Mock()
        stream.replication_method = "FULL_TABLE"
        stream.replication_key = None
        
        # Test the URL params method
        params = stream.get_url_params(context={"archived": False}, next_page_token=None)
        
        assert "limit" in params
        assert "filter" not in params

    def test_ensure_date_properties_included(self):
        """Test that date properties are always included in selected properties."""
        config = {
            "access_token": "test_token",
            "start_date": "2023-01-01T00:00:00Z"
        }
        
        # Create a properly mocked tap
        mock_tap = Mock()
        mock_tap.config = config
        mock_tap.logger = Mock()
        mock_tap.name = "tap-hubspot"
        
        # Create a stream instance
        stream = ContactsStream(tap=mock_tap)
        stream.name = "contacts"
        stream.logger = Mock()
        
        # Test with properties that don't include date properties
        test_properties = ["firstname", "lastname", "email"]
        result = stream._ensure_date_properties_included(test_properties)
        
        assert "firstname" in result
        assert "lastname" in result
        assert "email" in result
        assert "hs_createdate" in result
        assert "hs_lastmodifieddate" in result
        assert len(result) == 5

    def test_ensure_date_properties_included_already_present(self):
        """Test that date properties are not duplicated if already present."""
        config = {
            "access_token": "test_token",
            "start_date": "2023-01-01T00:00:00Z"
        }
        
        # Create a properly mocked tap
        mock_tap = Mock()
        mock_tap.config = config
        mock_tap.logger = Mock()
        mock_tap.name = "tap-hubspot"
        
        # Create a stream instance
        stream = ContactsStream(tap=mock_tap)
        stream.name = "contacts"
        stream.logger = Mock()
        
        # Test with properties that already include date properties
        test_properties = ["firstname", "hs_createdate", "hs_lastmodifieddate"]
        result = stream._ensure_date_properties_included(test_properties)
        
        assert "firstname" in result
        assert "hs_createdate" in result
        assert "hs_lastmodifieddate" in result
        assert len(result) == 3  # No duplicates 