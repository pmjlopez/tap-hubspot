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
        
        # If using POST method, don't include properties in URL params
        if self._should_use_post_method():
            # Only include basic pagination and filtering in URL for POST
            if next_page_token:
                params["after"] = next_page_token
            
            # Add date filtering if this is an incremental stream with a start_date
            if self.replication_method == "INCREMENTAL" and self.replication_key:
                date_filter = self._get_date_filter_params()
                if date_filter:
                    params.update(date_filter)
        else:
            # For GET method, include everything in URL params
            if next_page_token:
                params["after"] = next_page_token
            params["limit"] = 100
            
            # Add date filtering if this is an incremental stream with a start_date
            if self.replication_method == "INCREMENTAL" and self.replication_key:
                date_filter = self._get_date_filter_params()
                if date_filter:
                    params.update(date_filter)
        
        return params
    
    def _get_date_filter_params(self) -> Optional[Dict[str, Any]]:
        """Get date filtering parameters based on start_date from config."""
        try:
            start_date = self.config.get("start_date")
            if not start_date:
                return None
            
            # Convert start_date to timestamp for API filtering
            if isinstance(start_date, str):
                from singer_sdk._singerlib.utils import strptime_to_utc
                start_timestamp = strptime_to_utc(start_date)
            else:
                start_timestamp = start_date
            
            # Convert to milliseconds timestamp for HubSpot API
            start_ms = int(start_timestamp.timestamp() * 1000)
            
            # HubSpot CRM v3 API supports filtering by hs_createdate and hs_lastmodifieddate
            # We'll filter for records that were either created OR modified after the start_date
            # This ensures we don't miss records that were created before but modified after start_date
            filter_params = {
                "filter": f"(hs_createdate>={start_ms} OR hs_lastmodifieddate>={start_ms})"
            }
            
            self.logger.info(
                f"Stream '{self.name}': Adding date filter for records created or modified after {start_date} "
                f"(timestamp: {start_ms})"
            )
            
            return filter_params
            
        except Exception as e:
            self.logger.warning(
                f"Stream '{self.name}': Failed to add date filtering: {e}. "
                "Continuing without date filter."
            )
            return None
    
    def get_selected_properties(self) -> List[str]:
        """Get properties to sync based on configuration selection."""
        try:
            # First, check if we have a catalog file with metadata
            if hasattr(self, 'catalog') and self.catalog:
                # Find the stream in the catalog
                for stream in self.catalog.get('streams', []):
                    if stream.get('tap_stream_id') == self.name:
                        # Get selected properties from metadata
                        selected_properties = []
                        metadata = stream.get('metadata', [])
                        
                        for meta in metadata:
                            breadcrumb = meta.get('breadcrumb', [])
                            if len(breadcrumb) == 2 and breadcrumb[0] == 'properties':
                                property_name = breadcrumb[1]
                                if meta.get('metadata', {}).get('selected', False):
                                    selected_properties.append(property_name)
                        
                        if selected_properties:
                            self.logger.info(
                                f"Stream '{self.name}': {len(selected_properties)} properties selected "
                                f"from catalog metadata: {selected_properties[:5]}{'...' if len(selected_properties) > 5 else ''}"
                            )
                            return self._ensure_date_properties_included(selected_properties)
            
            # Second, check if we have selected_properties in config
            config_selected_properties = self.config.get('selected_properties', {})
            if config_selected_properties and self.name in config_selected_properties:
                selected_properties = config_selected_properties[self.name]
                if selected_properties:
                    self.logger.info(
                        f"Stream '{self.name}': {len(selected_properties)} properties selected "
                        f"from config: {selected_properties[:5]}{'...' if len(selected_properties) > 5 else ''}"
                    )
                    return self._ensure_date_properties_included(selected_properties)
            
            # If no properties are explicitly selected, use a default set of essential properties
            # This prevents URI length issues while still getting the most important data
            try:
                available_properties = [prop["name"] for prop in self.get_properties()]
                default_properties = self._get_default_properties()
                valid_selected_properties = list(set(default_properties).intersection(available_properties))
                
                self.logger.info(
                    f"Stream '{self.name}': No properties explicitly selected, "
                    f"using {len(valid_selected_properties)} default properties out of {len(available_properties)} available"
                )
                
                return self._ensure_date_properties_included(valid_selected_properties)
            except Exception as e:
                self.logger.warning(
                    f"Stream '{self.name}': Failed to get available properties, using default properties. Error: {e}"
                )
                # Return default properties without validation if API call fails
                return self._get_default_properties()
            
        except Exception as e:
            # Fallback to default properties if anything fails
            self.logger.warning(
                f"Stream '{self.name}': Failed to read property selection, using default properties. Error: {e}"
            )
            return self._get_default_properties()
    
    def _ensure_date_properties_included(self, properties: List[str]) -> List[str]:
        """Ensure that date properties needed for filtering are always included."""
        date_properties = ['hs_createdate', 'hs_lastmodifieddate']
        result = properties.copy()
        
        for prop in date_properties:
            if prop not in result:
                result.append(prop)
                self.logger.debug(f"Stream '{self.name}': Added required date property '{prop}' for filtering")
        
        return result

    def prepare_request_payload(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Optional[dict]:
        """Prepare the data payload for the REST API request.

        For HubSpot CRM v3 API, we can use POST to avoid URL length issues
        when there are many properties selected.
        """
        # Check if we should use POST method (when there are many properties)
        if self._should_use_post_method():
            selected_properties = self.get_selected_properties()
            
            payload = {
                "properties": selected_properties,
                "limit": 100
            }
            
            # Add date filtering if applicable
            if self.replication_method == "INCREMENTAL" and self.replication_key:
                date_filter = self._get_date_filter_params()
                if date_filter:
                    # Convert filter string to HubSpot's POST format
                    filter_str = date_filter["filter"]
                    payload["filter"] = filter_str
            
            # Add pagination if needed
            if next_page_token:
                payload["after"] = next_page_token
            
            # Add archived status if available
            if context and "archived" in context:
                payload["archived"] = context["archived"]
            
            # Add associations if this stream uses them
            if hasattr(self, 'path') and 'objects' in self.path:
                payload["associations"] = HUBSPOT_OBJECTS
            
            self.logger.info(
                f"Stream '{self.name}': Using POST method with {len(selected_properties)} properties "
                f"to avoid URL length issues"
            )
            
            return payload
        
        return None
    
    def _should_use_post_method(self) -> bool:
        """Determine if we should use POST method instead of GET."""
        # Use POST if we have more than 50 properties to avoid URL length issues
        selected_properties = self.get_selected_properties()
        return len(selected_properties) > 50
    
    @property
    def http_method(self) -> str:
        """Return the HTTP method to use for this stream."""
        if self._should_use_post_method():
            return "POST"
        return "GET"

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
        params = []

        # Get the properties that should be included based on selection
        selected_property_names = self.get_selected_properties()
        
        # Store the selected properties for use in URL params
        self.properties = selected_property_names
        
        # If we have selected properties, use them directly
        if selected_property_names:
            # Try to get property types from API, but don't fail if it doesn't work
            try:
                properties_hub = self.get_properties()
                property_types = {prop["name"]: prop["type"] for prop in properties_hub}
            except Exception as e:
                self.logger.warning(f"Failed to get property types from API: {e}. Using string type for all properties.")
                property_types = {}
            
            for name in selected_property_names:
                params.append(name)
                # Use the property type from API if available, otherwise default to string
                prop_type = property_types.get(name, "string")
                type = self.get_json_schema(prop_type)
                if name in poorly_cast:
                    internal_properties.append(th.Property(name, th.StringType()))
                else:
                    internal_properties.append(th.Property(name, type))
        else:
            # Fallback to getting all properties if none are selected
            try:
                properties_hub = self.get_properties()
                for prop in properties_hub:
                    name = prop["name"]
                    params.append(name)
                    type = self.get_json_schema(prop["type"])
                    if name in poorly_cast:
                        internal_properties.append(th.Property(name, th.StringType()))
                    else:
                        internal_properties.append(th.Property(name, type))
            except Exception as e:
                self.logger.warning(f"Failed to get properties from API: {e}")
        
        objects = HUBSPOT_OBJECTS

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

    def _get_default_properties(self) -> List[str]:
        """Get default properties for each stream to prevent URI length issues."""
        default_properties_map = {
            'deals': [
                'dealname',
                'amount',
                'dealstage',
                'closedate',
                'pipeline',
                'hs_is_closed',
                'hs_is_closed_won',
                'hs_is_closed_lost',
                'hs_deal_stage_probability',
                'hs_createdate',
                'hs_lastmodifieddate'
            ],
            'contacts': [
                'firstname',
                'lastname',
                'email',
                'phone',
                'company',
                'jobtitle',
                'hs_createdate',
                'hs_lastmodifieddate'
            ],
            'companies': [
                'name',
                'domain',
                'industry',
                'city',
                'state',
                'country',
                'hs_createdate',
                'hs_lastmodifieddate'
            ],
            'meetings': [
                'hs_timestamp',
                'hs_meeting_title',
                'hs_meeting_body',
                'hs_meeting_start_time',
                'hs_meeting_end_time',
                'hs_createdate',
                'hs_lastmodifieddate'
            ],
            'calls': [
                'hs_call_title',
                'hs_call_body',
                'hs_call_duration',
                'hs_call_start_time',
                'hs_call_end_time',
                'hs_createdate',
                'hs_lastmodifieddate'
            ],
            'quotes': [
                'hs_title',
                'hs_amount',
                'hs_expiration_date',
                'hs_status',
                'hs_createdate',
                'hs_lastmodifieddate'
            ],
            'line_items': [
                'hs_product_id',
                'hs_quantity',
                'hs_cost',
                'hs_price',
                'hs_createdate',
                'hs_lastmodifieddate'
            ]
        }
        
        # Always include date properties for filtering if not already present
        base_properties = default_properties_map.get(self.name, [])
        date_properties = ['hs_createdate', 'hs_lastmodifieddate']
        
        for prop in date_properties:
            if prop not in base_properties:
                base_properties.append(prop)
        
        return base_properties

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
