# tap-hubspot

`tap-hubspot` is a Singer tap for Hubspot.

Built with the [Meltano Tap SDK](https://sdk.meltano.com) for Singer Taps.

## What is this fork for?
### URI too long
In my case Hubspot users created a lot of fields making hundreds of properties, and putting these all as parameters will cause an error.
### start_date is ignored during fetching from Hubspot
Every time I run my pipeline it still gets everything each time then filters them after, pretty much a waste for time and resources.

## Capabilities

* `catalog`
* `state`
* `discover`
* `about`
* `stream-maps`
* `schema-flattening`

## Settings

| Setting             | Required | Default | Description |
|:--------------------|:--------:|:-------:|:------------|
| access_token        | True     | None    | PRIVATE Access Token for Hubspot API (TODO: Add public option) |
| start_date          | True     | None    | The earliest record date to sync |
| stream_maps         | False    | None    | Config object for stream maps capability. |
| stream_map_config   | False    | None    | User-defined config values to be used within map expressions. |
| flattening_enabled  | False    | None    | 'True' to enable schema flattening and automatically expand nested properties. |
| flattening_max_depth| False    | None    | The max depth to flatten schemas. |

A full list of supported settings and capabilities is available by running: `tap-hubspot --about`

## Configuring Properties in Meltano

When using this tap with Meltano, you can control which properties are synced for each object type using Meltano's `select` and `metadata` configuration. This allows you to limit the data being extracted to only the properties you need.

### Example: Limiting Contact Properties

To sync only specific contact properties, update your `meltano.yml`:

```yaml
plugins:
  extractors:
  - name: tap-hubspot
    namespace: tap_hubspot
    pip_url: -e .
    capabilities:
    - state
    - catalog
    - discover
    settings:
    - name: access_token
      kind: password
    - name: start_date
      value: '2010-01-01T00:00:00Z'
    config:
      start_date: '2010-01-01T00:00:00Z'
    select:
      # Select only specific contact properties
      - contacts.properties.firstname
      - contacts.properties.lastname
      - contacts.properties.email
      - contacts.properties.phone
      # Select all deal properties
      - deals.*
      # Select all quote properties
      - quotes.*
```

### Example: Limiting Multiple Object Types

```yaml
plugins:
  extractors:
  - name: tap-hubspot
    namespace: tap_hubspot
    pip_url: -e .
    capabilities:
    - state
    - catalog
    - discover
    settings:
    - name: access_token
      kind: password
    - name: start_date
      value: '2010-01-01T00:00:00Z'
    config:
      start_date: '2010-01-01T00:00:00Z'
    select:
      # Contact properties
      - contacts.properties.firstname
      - contacts.properties.lastname
      - contacts.properties.email
      - contacts.properties.company
      # Company properties
      - companies.properties.name
      - companies.properties.domain
      - companies.properties.industry
      # Deal properties
      - deals.properties.dealname
      - deals.properties.amount
      - deals.properties.dealstage
      - deals.properties.closedate
```

### Property Selection Patterns

- `contacts.properties.*` - All contact properties
- `contacts.properties.firstname` - Specific contact property
- `deals.*` - All deal data (including properties, associations, etc.)
- `companies.properties.name` - Specific company property

### Discovering Available Properties

To see all available properties for each object type, run:

```bash
meltano invoke tap-hubspot --discover
```

This will show you the complete schema including all available properties that you can select.

# Setup

This is a [Singer](https://singer.io) tap that produces JSON-formatted data following the [Singer spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:
- Pulls raw data from HubSpot's [REST API](http://developers.hubspot.com/docs/overview)
- Extracts the following resources from HubSpot
  - [Campaigns](http://developers.hubspot.com/docs/methods/email/get_campaign_data)
  - [Companies](http://developers.hubspot.com/docs/methods/companies/get_company)
  - [Contacts](https://developers.hubspot.com/docs/methods/contacts/get_contacts)
  - [Contact Lists](http://developers.hubspot.com/docs/methods/lists/get_lists)
  - [Deals](http://developers.hubspot.com/docs/methods/deals/get_deals_modified)
  - [Meetings](https://developers.hubspot.com/docs/api/crm/meetings)
  - [Calls](https://developers.hubspot.com/docs/api/crm/calls)
  - [Deal Pipelines](https://developers.hubspot.com/docs/methods/deal-pipelines/get-all-deal-pipelines)
  - [Email Events](http://developers.hubspot.com/docs/methods/email/get_events)
  - [Forms](http://developers.hubspot.com/docs/methods/forms/v2/get_forms)
  - [Keywords](http://developers.hubspot.com/docs/methods/keywords/get_keywords)
  - [Owners](http://developers.hubspot.com/docs/methods/owners/get_owners)
  - [Subscription Changes](http://developers.hubspot.com/docs/methods/email/get_subscriptions_timeline)
  - [Workflows](http://developers.hubspot.com/docs/methods/workflows/v3/get_workflows)
- Outputs the schema for each resource
- Incrementally pulls data based on the input state

## Configuration

This tap requires a `config.json` which specifies details regarding [OAuth 2.0](https://developers.hubspot.com/docs/methods/oauth2/oauth2-overview) authentication, a cutoff date for syncing historical data, and an optional flag which controls collection of anonymous usage metrics. See [config.sample.json](config.sample.json) for an example. You may specify an API key instead of OAuth parameters for development purposes, as detailed below.

To run `tap-hubspot` with the configuration file, use this command:

```bash
› tap-hubspot -c my-config.json
```


## API Key Authentication (for development)

As an alternative to OAuth 2.0 authentication during development, you may specify an API key (`HAPIKEY`) to authenticate with the HubSpot API. This should be used only for low-volume development work, as the [HubSpot API Usage Guidelines](https://developers.hubspot.com/apps/api_guidelines) specify that integrations should use OAuth for authentication.

To use an API key, include a `hapikey` configuration variable in your `config.json` and set it to the value of your HubSpot API key. Any OAuth authentication parameters in your `config.json` **will be ignored** if this key is present!

---

Copyright &copy; 2017 Stitch

## Usage

You can easily run `tap-hubspot` by itself or in a pipeline using [Meltano](https://meltano.com/).

### Executing the Tap Directly

```bash
tap-hubspot --version
tap-hubspot --help
tap-hubspot --config CONFIG --discover > ./catalog.json
```

### Initialize your Development Environment

```bash
pipx install poetry
poetry install
```

### Create and Run Tests

Create tests within the `tap_hubspot/tests` subfolder and
  then run:

```bash
poetry run pytest
```

You can also test the `tap-hubspot` CLI interface directly using `poetry run`:

```bash
poetry run tap-hubspot --help
```

### Testing with [Meltano](https://www.meltano.com)

_**Note:** This tap will work in any Singer environment and does not require Meltano.
Examples here are for convenience and to streamline end-to-end orchestration scenarios._

Your project comes with a custom `meltano.yml` project file already created. Open the `meltano.yml` and follow any _"TODO"_ items listed in
the file.

Next, install Meltano (if you haven't already) and any needed plugins:

```bash
# Install meltano
pipx install meltano
# Initialize meltano within this directory
cd tap-hubspot
meltano install
```

Now you can test and orchestrate using Meltano:

```bash
# Test invocation:
meltano invoke tap-hubspot --version
# OR run a test `elt` pipeline:
meltano elt tap-hubspot target-jsonl
```

### SDK Dev Guide

See the [dev guide](https://sdk.meltano.com/en/latest/dev_guide.html) for more instructions on how to use the SDK to
develop your own taps and targets.
