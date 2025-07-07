#!/usr/bin/env python3
"""
Script to fix the catalog.json file by adding proper metadata for selected properties.
This ensures that the tap knows which properties are selected from the meltano.yml configuration.
"""

import json
import yaml
import sys
from pathlib import Path

def load_meltano_config():
    """Load the meltano.yml configuration file."""
    with open('meltano.yml', 'r') as f:
        return yaml.safe_load(f)

def load_catalog():
    """Load the current catalog.json file."""
    with open('catalog.json', 'r') as f:
        return json.load(f)

def save_catalog(catalog):
    """Save the updated catalog.json file."""
    with open('catalog.json', 'w') as f:
        json.dump(catalog, f, indent=2)

def get_selected_properties_from_meltano(meltano_config):
    """Extract selected properties from meltano.yml configuration."""
    selected_properties = {}
    
    # Get the select configuration from the tap-hubspot extractor
    for extractor in meltano_config.get('plugins', {}).get('extractors', []):
        if extractor.get('name') == 'tap-hubspot':
            select_config = extractor.get('select', [])
            
            for selection in select_config:
                # Parse the selection pattern (e.g., "deals.properties.amount")
                parts = selection.split('.')
                if len(parts) >= 2:
                    stream_name = parts[0]  # e.g., "deals"
                    if stream_name not in selected_properties:
                        selected_properties[stream_name] = []
                    
                    if len(parts) == 2 and parts[1] == '*':
                        # Wildcard selection (e.g., "deals.*")
                        selected_properties[stream_name].append('*')
                    elif len(parts) >= 3 and parts[1] == 'properties':
                        # Property selection (e.g., "deals.properties.amount")
                        property_name = '.'.join(parts[2:])
                        selected_properties[stream_name].append(property_name)
                    else:
                        # Direct field selection (e.g., "deals.id")
                        field_name = '.'.join(parts[1:])
                        selected_properties[stream_name].append(field_name)
    
    return selected_properties

def add_metadata_to_catalog(catalog, selected_properties):
    """Add metadata to the catalog streams based on selected properties."""
    # Get all available stream names from the catalog
    available_streams = [stream['tap_stream_id'] for stream in catalog['streams']]
    
    print(f"Available streams in catalog: {available_streams}")
    print(f"Selected streams from meltano.yml: {list(selected_properties.keys())}")
    
    for stream in catalog['streams']:
        stream_name = stream['tap_stream_id']
        
        # Check if this stream is in our selection
        is_stream_selected = stream_name in selected_properties
        
        if is_stream_selected:
            # Create metadata for this stream
            metadata = []
            
            # Add metadata for each property in the schema
            schema_properties = stream.get('schema', {}).get('properties', {})
            
            for prop_name in schema_properties.keys():
                # Check if this property is selected
                is_selected = False
                
                if '*' in selected_properties[stream_name]:
                    # Wildcard selection - select all properties
                    is_selected = True
                elif prop_name in selected_properties[stream_name]:
                    # Specific property selection
                    is_selected = True
                
                # Add metadata for this property
                metadata.append({
                    "breadcrumb": ["properties", prop_name],
                    "metadata": {
                        "selected": is_selected,
                        "inclusion": "automatic" if is_selected else "available"
                    }
                })
            
            # Add metadata for the stream itself
            metadata.append({
                "breadcrumb": [],
                "metadata": {
                    "selected": True,
                    "replication-key": stream.get('replication_key'),
                    "replication-method": stream.get('replication_method'),
                    "table-key-properties": stream.get('key_properties', [])
                }
            })
            
            # Add the metadata to the stream
            stream['metadata'] = metadata
            
            selected_prop_count = len([m for m in metadata if m['breadcrumb'] and m['metadata']['selected']])
            print(f"✓ Stream '{stream_name}' SELECTED with {selected_prop_count} selected properties")
        else:
            # Stream not in selection - mark as not selected
            metadata = []
            schema_properties = stream.get('schema', {}).get('properties', {})
            
            for prop_name in schema_properties.keys():
                metadata.append({
                    "breadcrumb": ["properties", prop_name],
                    "metadata": {
                        "selected": False,
                        "inclusion": "available"
                    }
                })
            
            metadata.append({
                "breadcrumb": [],
                "metadata": {
                    "selected": False,
                    "replication-key": stream.get('replication_key'),
                    "replication-method": stream.get('replication_method'),
                    "table-key-properties": stream.get('key_properties', [])
                }
            })
            
            stream['metadata'] = metadata
            print(f"✗ Stream '{stream_name}' NOT SELECTED")
    
    # Check for streams that were requested but don't exist
    missing_streams = set(selected_properties.keys()) - set(available_streams)
    if missing_streams:
        print(f"\n⚠️  WARNING: The following streams were requested but don't exist in the catalog:")
        for missing in missing_streams:
            print(f"   - {missing}")

def main():
    """Main function to fix the catalog file."""
    print("Loading meltano.yml configuration...")
    meltano_config = load_meltano_config()
    
    print("Loading catalog.json...")
    catalog = load_catalog()
    
    print("Extracting selected properties from meltano.yml...")
    selected_properties = get_selected_properties_from_meltano(meltano_config)
    
    print(f"Found selected properties: {selected_properties}")
    
    print("\nAdding metadata to catalog...")
    add_metadata_to_catalog(catalog, selected_properties)
    
    print("\nSaving updated catalog.json...")
    save_catalog(catalog)
    
    print("Catalog file has been updated successfully!")
    print("You can now use this catalog file with the tap using: --catalog catalog.json")

if __name__ == "__main__":
    main() 