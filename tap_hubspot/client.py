"""REST client handling, including HubspotStream base class."""
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import backoff
import pytz
import requests
from singer_sdk import typing as th
from singer_sdk._singerlib.utils import strptime_to_utc
from singer_sdk.authenticators import BearerTokenAuthenticator
from singer_sdk.exceptions import RetriableAPIError
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")
HUBSPOT_OBJECTS = [
    "deals",
    "companies",
    "contacts",
    "meetings",
    "quotes",
    "calls",
    "notes",
    "tasks",
    "emails",
]


class HubspotStream(RESTStream):
    """Hubspot stream class."""

    url_base = "https://api.hubapi.com"

    records_jsonpath = "$.results[*]"  # Or override `parse_response`.
    next_page_token_jsonpath = (
        "$.paging.next.after"  # Or override `get_next_page_token`.
    )
    replication_key = "updatedAt"
    replication_method = "INCREMENTAL"
    cached_schema = None
    properties = []

    @property
    def schema_filepath(self) -> Path:
        return SCHEMAS_DIR / f"{self.name}.json"

    @property
    def authenticator(self) -> BearerTokenAuthenticator:
        """Return a new authenticator object."""
        return BearerTokenAuthenticator.create_for_stream(
            self,
            token=self.config.get("access_token"),
        )

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        if "access_token" in self.config:
            headers["Authorization"] = f"Bearer {self.config.get('access_token')}"
        return headers

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Optional[Any]:
        """Return a token for identifying next page or None if no more pages."""
        if self.next_page_token_jsonpath:
            all_matches = extract_jsonpath(
                self.next_page_token_jsonpath, response.json()
            )
            first_match = next(iter(all_matches), None)
            next_page_token = first_match
        else:
            next_page_token = response.headers.get("X-Next-Page", None)

        return next_page_token

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        if next_page_token:
            params["after"] = next_page_token
        params["limit"] = 100
        return params
    
    def get_selected_properties(self) -> List[str]:
        """Get properties to sync based on metadata selection (Meltano compatible)."""
        # Get properties selected via metadata (Meltano select/metadata)
        selected_properties = [
            key[-1] for key, value in self.metadata.items()
            if value.selected and len(key) > 0
        ]
        
        # Filter to only include properties that actually exist in HubSpot
        available_properties = [prop["name"] for prop in self.get_properties()]
        valid_selected_properties = list(set(selected_properties).intersection(available_properties))
        
        # Log information about property selection
        if selected_properties:
            self.logger.info(
                f"Stream '{self.name}': {len(valid_selected_properties)} properties selected "
                f"out of {len(available_properties)} available properties"
            )
            
            # Log warning for invalid properties
            invalid_properties = [prop for prop in selected_properties if prop not in available_properties]
            if invalid_properties:
                self.logger.warning(
                    f"Stream '{self.name}': Invalid properties in selection: {invalid_properties}. "
                    f"These properties don't exist in HubSpot and will be ignored."
                )
        else:
            self.logger.info(
                f"Stream '{self.name}': No properties explicitly selected, "
                f"will use all available properties ({len(available_properties)} total)"
            )
            # If no properties are selected, use all available properties
            valid_selected_properties = available_properties
        
        return valid_selected_properties

    def prepare_request_payload(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Optional[dict]:
        """Prepare the data payload for the REST API request.

        By default, no payload will be sent (return None).
        """
        return None

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        yield from extract_jsonpath(self.records_jsonpath, input=response.json())

    def get_json_schema(self, from_type: str) -> dict:
        """Return the JSON Schema dict that describes the sql type.

        Args:
            from_type: The SQL type as a string or as a TypeEngine. If a TypeEngine is
                provided, it may be provided as a class or a specific object instance.

        Raises:
            ValueError: If the `from_type` value is not of type `str` or `TypeEngine`.

        Returns:
            A compatible JSON Schema type definition.
        """
        sqltype_lookup: Dict[str, dict] = {
            # NOTE: This is an ordered mapping, with earlier mappings taking precedence.
            #       If the SQL-provided type contains the type name on the left, the mapping
            #       will return the respective singer type.
            "timestamp": th.DateTimeType(),
            "datetime": th.DateTimeType(),
            "date": th.DateType(),
            "int": th.IntegerType(),
            "number": th.NumberType(),
            "decimal": th.NumberType(),
            "double": th.NumberType(),
            "float": th.NumberType(),
            "string": th.StringType(),
            "text": th.StringType(),
            "char": th.StringType(),
            "bool": th.BooleanType(),
            "variant": th.StringType(),
        }
        sqltype_lookup_hubspot: Dict[str, dict] = {
            # "timestamp": th.DateTimeType(),
            # "datetime": th.DateTimeType(),
            # "date": th.DateType(),
            "string": th.StringType(),
            # "bool": th.BooleanType(),
            # "variant": th.StringType(),
        }
        if isinstance(from_type, str):
            type_name = from_type
        else:
            raise ValueError(
                "Expected `str` or a SQLAlchemy `TypeEngine` object or type."
            )
        for sqltype, jsonschema_type in sqltype_lookup_hubspot.items():
            if sqltype.lower() in type_name.lower():
                return jsonschema_type
        return sqltype_lookup["string"]  # safe failover to str

    def get_custom_schema(self, poorly_cast: List[str] = []):
        """Dynamically detect the json schema for the stream.
        This is evaluated prior to any records being retrieved.

        Returns: Parameters to be included in query + schema property list
        """
        internal_properties: List[th.Property] = []
        properties: List[th.Property] = []

        properties_hub = self.get_properties()
        objects = HUBSPOT_OBJECTS
        params = []

        # Get the properties that should be included based on selection
        selected_property_names = self.get_selected_properties()
        
        # Store the selected properties for use in URL params
        self.properties = selected_property_names

        for prop in properties_hub:
            name = prop["name"]
            # Only include properties that are selected
            if name in selected_property_names:
                params.append(name)
                type = self.get_json_schema(prop["type"])
                if name in poorly_cast:
                    internal_properties.append(th.Property(name, th.StringType()))
                else:
                    internal_properties.append(th.Property(name, type))

        properties.append(th.Property("updatedAt", th.DateTimeType()))
        properties.append(th.Property("createdAt", th.DateTimeType()))
        properties.append(th.Property("id", th.StringType()))
        properties.append(th.Property("archived", th.BooleanType()))

        # Add in associations
        associations_properties = []

        for obj in objects:
            associations_properties.append(
                th.Property(
                    f"{obj}",
                    th.ObjectType(
                        th.Property(
                            "results",
                            th.ArrayType(
                                th.ObjectType(
                                    th.Property("id", th.StringType()),
                                    th.Property("type", th.StringType()),
                                )
                            ),
                        )
                    ),
                ),
            )
        properties.append(
            th.Property("associations", th.ObjectType(*associations_properties))
        )
        properties.append(
            th.Property("properties", th.ObjectType(*internal_properties))
        )
        return th.PropertiesList(*properties).to_dict(), params

    def get_properties(self) -> List[dict]:
        response = requests.get(
            f"{self.url_base}/crm/v3/properties/{self.name}", headers=self.http_headers
        )
        try:
            data = response.json()
            response.raise_for_status()
            return data.get("results", [])
        except requests.exceptions.HTTPError as e:
            self.logger.warning(
                "Dynamic discovery of properties failed with an exception, "
                f"continuing gracefully with no dynamic properties: {e}, {data}"
            )
            return []

    def get_params_from_properties(self, properties: List[dict]) -> List[str]:
        params = []
        for prop in properties:
            params.append(prop["name"])
        return params

    def request_decorator(self, func: Callable) -> Callable:
        """Instantiate a decorator for handling request failures.

        Uses a wait generator defined in `backoff_wait_generator` to
        determine backoff behaviour. Try limit is defined in
        `backoff_max_tries`, and will trigger the event defined in
        `backoff_handler` before retrying. Developers may override one or
        all of these methods to provide custom backoff or retry handling.

        Args:
            func: Function to decorate.

        Returns:
            A decorated method.
        """
        decorator: Callable = backoff.on_exception(
            self.backoff_wait_generator,
            (
                RetriableAPIError,
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError,
            ),
            max_tries=self.backoff_max_tries,
            on_backoff=self.backoff_handler,
        )(func)
        return decorator
