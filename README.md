# tap-hubspot

`tap-hubspot` is a Singer tap for HubSpot, built with the [Meltano Tap SDK](https://sdk.meltano.com) for Singer Taps.

## 🚀 This Fork: Enhanced HubSpot Integration

This is a **fork of the original tap-hubspot** that addresses critical limitations in the original implementation, specifically designed for organizations with large HubSpot instances that have hundreds of custom properties.

### Why This Fork Was Created

The original tap-hubspot has several limitations that become problematic for enterprise HubSpot instances:

1. **URI Length Limitations**: When HubSpot instances have hundreds of custom properties, the original tap fails with "URI too long" errors
2. **Inefficient Date Filtering**: The original tap fetches all data and filters client-side, wasting time and resources
3. **Property Count Restrictions**: Artificial limits prevent accessing all available properties

### Key Differentiators from Original

| Feature | Original tap-hubspot | This Fork |
|---------|---------------------|-----------|
| **Property Handling** | GET requests with URL parameters | POST requests with search endpoints |
| **URI Length** | Fails with 50+ properties | Handles 600+ properties efficiently |
| **Date Filtering** | Client-side filtering | API-level filtering |
| **Property Limits** | Limited property selection | All properties available |
| **Performance** | Inefficient for large datasets | Optimized for enterprise scale |

## ✅ Problems Solved

### 1. URI Too Long - SOLVED ✅
**Problem**: HubSpot instances with hundreds of custom properties cause "URI too long" errors when using GET requests.

**Solution**: Implemented search endpoint pattern that uses POST requests for all streams, sending properties in the request body instead of URL parameters.

### 2. Inefficient Date Filtering - SOLVED ✅
**Problem**: Original tap fetches all data and filters client-side, wasting time and resources.

**Solution**: Implemented API-level date filtering using `hs_createdate` and `hs_lastmodifieddate` properties, filtering at the API level instead of client-side.

### 3. Property Count Limitations - SOLVED ✅
**Problem**: Artificial limits on the number of properties that can be synced.

**Solution**: Removed all property count restrictions. The tap now automatically uses all available properties for each stream and efficiently handles them using POST requests.

## 🔧 Technical Improvements

### 🚀 Search Endpoint Pattern
- All CRM object streams now use `/search` endpoints
- Automatic POST method for efficient property handling
- Eliminates URI length limitations completely
- Consistent pattern across all streams

### 📅 API-Level Date Filtering
- Uses `hs_createdate` and `hs_lastmodifieddate` for efficient filtering
- Filters at the API level instead of client-side
- Respects `start_date` configuration properly
- Reduces data transfer and processing time

### 🔥 Full Property Access
- No artificial limits on property count
- Automatically uses all available properties for each stream
- Efficient handling of large property sets (600+ properties per stream)
- Maintains backward compatibility with property selection

### 🏗️ Enhanced Architecture
- Updated base `HubspotStream` class with improved logic
- Search endpoint support for all major CRM objects
- Better error handling and logging
- Improved pagination and state management

## 📊 Supported Streams

All major HubSpot CRM objects now use the optimized search endpoint pattern:

- **Companies** - `/crm/v3/objects/companies/search`
- **Contacts** - `/crm/v3/objects/contacts/search`
- **Deals** - `/crm/v3/objects/deals/search`
- **Calls** - `/crm/v3/objects/calls/search`
- **Meetings** - `/crm/v3/objects/meetings/search`
- **Quotes** - `/crm/v3/objects/quotes/search`
- **Line Items** - `/crm/v3/objects/line_items/search`
- **Notes** - `/crm/v3/objects/notes/search`
- **Tasks** - `/crm/v3/objects/tasks/search`
- **Emails** - `/crm/v3/objects/emails/search`

## 🚀 Performance Benefits

- **Eliminates URI Length Errors**: POST method handles unlimited properties
- **Faster Data Extraction**: API-level filtering reduces data transfer
- **Better Resource Utilization**: Efficient pagination and state management
- **Enterprise Scale Ready**: Handles large HubSpot instances with hundreds of properties

## 📋 Configuration

### Basic Configuration

```json
{
  "access_token": "your-hubspot-access-token",
  "start_date": "2020-01-01T00:00:00Z"
}
```

### Environment Variables

```bash
export TAP_HUBSPOT_ACCESS_TOKEN="your-access-token"
export TAP_HUBSPOT_START_DATE="2020-01-01T00:00:00Z"
```

## 🔧 Installation

### Using Poetry (Recommended)

```bash
# Install dependencies
poetry install

# Run the tap
poetry run tap-hubspot --config config.json --discover
```

### Using pip

```bash
# Install the package
pip install -e .

# Run the tap
tap-hubspot --config config.json --discover
```

## 🧪 Testing

### Run Tests

```bash
poetry run pytest
```

### Test with Meltano

```bash
# Install meltano
pipx install meltano

# Initialize project
meltano install

# Test the tap
meltano invoke tap-hubspot --discover
```

## 📈 Usage Examples

### Discover Schema

```bash
tap-hubspot --config config.json --discover > catalog.json
```

### Extract Data

```bash
tap-hubspot --config config.json --catalog catalog.json
```

### With Meltano

```bash
meltano elt tap-hubspot target-jsonl
```

## 🔍 Property Selection

You can still control which properties are synced using Meltano's select configuration:

```yaml
select:
  # Select specific properties
  - contacts.properties.firstname
  - contacts.properties.lastname
  - contacts.properties.email
  
  # Select all properties for a stream
  - deals.*
  - companies.*
```

## 🤝 Contributing

This fork maintains compatibility with the original tap-hubspot while adding enterprise-scale improvements. Contributions are welcome!

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd tap-hubspot

# Install dependencies
poetry install

# Run tests
poetry run pytest
```

## 📄 License

This project is licensed under the same terms as the original tap-hubspot.

## 🙏 Acknowledgments

- Original tap-hubspot maintainers for the foundation
- HubSpot API team for the comprehensive search endpoints
- Meltano team for the excellent SDK

---

**Note**: This fork is specifically designed for enterprise HubSpot instances with large numbers of custom properties. For smaller instances, the original tap-hubspot may be sufficient.
