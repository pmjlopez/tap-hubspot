"""Hubspot tap class."""

import json
from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th

from tap_hubspot.analytics_streams import AnalyticsViewsStream
from tap_hubspot.automation_streams import WorkflowsStream
from tap_hubspot.events_streams import (
    WebAnalyticsContactsStream,
    WebAnalyticsDealsStream,
)
from tap_hubspot.marketing_streams import (
    MarketingCampaignIdsStream,
    MarketingCampaignsStream,
    MarketingEmailsStream,
    MarketingFormsStream,
    MarketingListContactsStream,
    MarketingListsStream,
)
from tap_hubspot.streams import (
    AssociationsCompaniesToContactsStream,
    AssociationsCompaniesToDealsStream,
    AssociationsContactsToCompaniesStream,
    AssociationsContactsToDealsStream,
    AssociationsDealsToCompaniesStream,
    AssociationsDealsToContactsStream,
    CallsStream,
    CompaniesStream,
    ContactsStream,
    DealsStream,
    EmailsStream,
    LineItemsStream,
    MeetingsStream,
    NotesStream,
    OwnersStream,
    PropertiesCompaniesStream,
    PropertiesContactsStream,
    PropertiesDealsStream,
    PropertiesMeetingsStream,
    QuotesStream,
    TasksStream,
)

# from black import main

STREAM_TYPES = [
    ## CRM
    AssociationsCompaniesToContactsStream,
    AssociationsCompaniesToDealsStream,
    AssociationsContactsToCompaniesStream,
    AssociationsContactsToDealsStream,
    AssociationsDealsToCompaniesStream,
    AssociationsDealsToContactsStream,
    ContactsStream,
    CompaniesStream,
    DealsStream,
    EmailsStream,
    LineItemsStream,
    MeetingsStream,
    NotesStream,
    QuotesStream,
    TasksStream,
    CallsStream,
    PropertiesCompaniesStream,
    PropertiesContactsStream,
    PropertiesDealsStream,
    PropertiesMeetingsStream,
    OwnersStream,
    ## Marketing
    MarketingEmailsStream,
    MarketingCampaignIdsStream,
    MarketingCampaignsStream,
    MarketingFormsStream,
    MarketingListsStream,
    MarketingListContactsStream,
    # Events
    WebAnalyticsContactsStream,
    WebAnalyticsDealsStream,
    ## Analytics
    AnalyticsViewsStream,
    ## Automation
    WorkflowsStream,
]


class TapHubspot(Tap):
    """Hubspot tap class."""

    name = "tap-hubspot"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "access_token",
            th.StringType,
            required=True,
            description="PRIVATE Access Token for Hubspot API",
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            required=True,
            description="The earliest record date to sync",
        ),
        th.Property(
            "selected_properties",
            th.ObjectType(
                th.Property("call_dispositions", th.ArrayType(th.StringType), required=False),
                th.Property("calls", th.ArrayType(th.StringType), required=False),
                th.Property("companies", th.ArrayType(th.StringType), required=False),
                th.Property("contacts", th.ArrayType(th.StringType), required=False),
                th.Property("deals", th.ArrayType(th.StringType), required=False),
                th.Property("emails", th.ArrayType(th.StringType), required=False),
                th.Property("line_items", th.ArrayType(th.StringType), required=False),
                th.Property("meetings", th.ArrayType(th.StringType), required=False),
                th.Property("notes", th.ArrayType(th.StringType), required=False),
                th.Property("owners", th.ArrayType(th.StringType), required=False),
                th.Property("quotes", th.ArrayType(th.StringType), required=False),
                th.Property("stages", th.ArrayType(th.StringType), required=False),
                th.Property("tasks", th.ArrayType(th.StringType), required=False),
            ),
            required=False,
            description="Object mapping stream names to arrays of property names to sync. With POST method support, you can now sync all available properties without URI length concerns.",
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        streams = []
        
        # Load catalog if provided
        catalog = None
        if hasattr(self, 'catalog_path') and self.catalog_path:
            try:
                with open(self.catalog_path, 'r') as f:
                    catalog = json.load(f)
                self.logger.info(f"Loaded catalog from {self.catalog_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load catalog from {self.catalog_path}: {e}")
        
        # Create streams with catalog
        for stream_class in STREAM_TYPES:
            stream = stream_class(tap=self)
            if catalog:
                stream.catalog = catalog
            streams.append(stream)
        
        return streams


if __name__ == "__main__":
    TapHubspot.cli()
