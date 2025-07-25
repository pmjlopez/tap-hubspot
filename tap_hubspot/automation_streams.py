"""Stream type classes for tap-hubspot."""
# from black import Report
from math import inf
import requests

import datetime, pytz
from datetime import datetime

from pathlib import Path
from typing import Optional, Iterable

from singer_sdk import typing as th  # JSON Schema typing helpers
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Iterable

from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk import typing as th  # JSON schema typing helpers
from tap_hubspot.client import HubspotStream

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")

utc=pytz.UTC

from tap_hubspot.schemas.automation import (
    Workflows,
)
class AutomationStream(HubspotStream):
    records_jsonpath = "$.workflows[*]"  # Or override `parse_response`.
    schema_filepath = ""

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        self.total_emails = response.json()['workflows']
        data = response.json()
        ret = [dict(d, updatedAt=datetime.fromtimestamp(d["updatedAt"]/1000, tz=utc)) for d in data["workflows"]]
        data["workflows"] = ret
        yield from extract_jsonpath(self.records_jsonpath, input=data)


    def post_process(self, row: dict, context: Optional[dict]) -> dict:
        """As needed, append or transform raw data to match expected structure.
        Returns row, or None if row is to be excluded"""
        
        # Note: Date filtering is now handled at the API level in the base HubspotStream class
        return row

class WorkflowsStream(AutomationStream):
    name = "workflows_v3"
    path = "/automation/v3/workflows"
    primary_keys = ["id"]
    schema = Workflows.schema
    replication_key = "updatedAt"


