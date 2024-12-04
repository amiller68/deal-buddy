import pytest
from src.llm.utils.json_helpers import parse_llm_json_response, ParseLLMJsonResponseException
import json

def test_parse_summary_json():
    # Test valid summary JSON
    json_str = """
    {
        "address": "123 Main Street, New York, NY 10001",
        "title": "Prime Office Building",
        "description": "Class A office building in Midtown Manhattan",
        "summary": "Recently renovated 20-story office tower",
        "square_feet": 250000,
        "year_built": 1985,
        "occupancy_rate": 95.5,
        "property_type": "office"
    }
    """
    result = parse_llm_json_response(
        json_str, 
        keys=["address", "title", "description", "summary"]
    )
    assert isinstance(result, dict)
    assert result["address"] == "123 Main Street, New York, NY 10001"
    assert result["title"] == "Prime Office Building"
    assert result["square_feet"] == 250000

def test_parse_summary_minimal_json():
    # Test JSON with only required fields
    json_str = """
    {
        "address": "123 Main Street",
        "title": "Office Building",
        "description": "Commercial property",
        "summary": "Basic summary"
    }
    """
    result = parse_llm_json_response(
        json_str, 
        keys=["address", "title", "description", "summary"]
    )
    assert isinstance(result, dict)
    assert result["address"] == "123 Main Street"
    assert "square_feet" not in result
    assert "year_built" not in result

def test_parse_summary_missing_required():
    # Test JSON missing required fields
    json_str = """
    {
        "address": "123 Main Street",
        "title": "Office Building"
    }
    """
    with pytest.raises(ParseLLMJsonResponseException) as exc_info:
        parse_llm_json_response(
            json_str, 
            keys=["address", "title", "description", "summary"]
        )

def test_parse_summary_with_markdown():
    # Test JSON wrapped in markdown
    json_str = """```json
    {
        "address": "123 Main Street",
        "title": "Office Building",
        "description": "Commercial property",
        "summary": "Basic summary"
    }
    ```"""
    result = parse_llm_json_response(
        json_str, 
        keys=["address", "title", "description", "summary"]
    )
    assert isinstance(result, dict)
    assert result["address"] == "123 Main Street"

def test_parse_summary_with_extra_fields():
    # Test JSON with additional fields
    json_str = """
    {
        "address": "123 Main Street",
        "title": "Office Building",
        "description": "Commercial property",
        "summary": "Basic summary",
        "extra_field": "should be allowed",
        "nested": {
            "data": "is fine too"
        }
    }
    """
    result = parse_llm_json_response(
        json_str, 
        keys=["address", "title", "description", "summary"]
    )
    assert isinstance(result, dict)
    assert result["extra_field"] == "should be allowed"
    assert result["nested"]["data"] == "is fine too"

def test_parse_summary_malformed_json():
    # Test malformed JSON
    json_str = """
    {
        "address": "123 Main Street",
        missing quotes and commas
        "title": "Office Building"
    }
    """
    with pytest.raises(ParseLLMJsonResponseException) as exc_info:
        parse_llm_json_response(
            json_str, 
            keys=["address", "title", "description", "summary"]
        )
