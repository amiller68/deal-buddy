import pytest
from pydantic import BaseModel
from typing import Optional, List
from src.llm.utils.json_helpers import parse_llm_json_response, ParseLLMJsonResponseException

class TestModel(BaseModel):
    required_str: str
    required_int: int
    optional_str: Optional[str] = None
    optional_list: List[str] = []
    optional_nested: Optional[dict] = None

def test_parse_json_with_model():
    # Test valid JSON with all fields
    json_str = """
    {
        "required_str": "hello",
        "required_int": 42,
        "optional_str": "world",
        "optional_list": ["a", "b"],
        "optional_nested": {"key": "value"}
    }
    """
    result = parse_llm_json_response(json_str, TestModel)
    assert isinstance(result, TestModel)
    assert result.required_str == "hello"
    assert result.required_int == 42
    assert result.optional_str == "world"
    assert result.optional_list == ["a", "b"]
    assert result.optional_nested == {"key": "value"}

def test_parse_json_with_minimal_fields():
    # Test valid JSON with only required fields
    json_str = """
    {
        "required_str": "hello",
        "required_int": 42
    }
    """
    result = parse_llm_json_response(json_str, model=TestModel)
    assert isinstance(result, TestModel)
    assert result.required_str == "hello"
    assert result.required_int == 42
    assert result.optional_str is None
    assert result.optional_list == []
    assert result.optional_nested is None

def test_parse_json_without_model():
    # Test parsing without model validation
    json_str = """
    {
        "any_key": "any_value",
        "nested": {"foo": "bar"}
    }
    """
    result = parse_llm_json_response(json_str)
    assert isinstance(result, dict)
    assert result["any_key"] == "any_value"
    assert result["nested"]["foo"] == "bar"

def test_parse_json_array():
    # Test parsing JSON array
    json_str = """
    [
        {"id": 1, "name": "first"},
        {"id": 2, "name": "second"}
    ]
    """
    result = parse_llm_json_response(json_str)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["name"] == "second"

def test_parse_json_with_markdown():
    # Test parsing JSON wrapped in markdown code block
    json_str = """```json
    {
        "required_str": "hello",
        "required_int": 42
    }
    ```"""
    result = parse_llm_json_response(json_str, model=TestModel)
    assert isinstance(result, TestModel)
    assert result.required_str == "hello"
    assert result.required_int == 42

def test_parse_invalid_json():
    # Test invalid JSON
    json_str = """
    {
        "invalid": json,
        syntax here
    }
    """
    with pytest.raises(ParseLLMJsonResponseException):
        parse_llm_json_response(json_str)

def test_parse_json_with_missing_required_fields():
    # Test JSON missing required fields
    json_str = """
    {
        "required_str": "hello"
    }
    """
    with pytest.raises(ParseLLMJsonResponseException):
        parse_llm_json_response(json_str, model=TestModel)

def test_parse_json_with_invalid_types():
    # Test JSON with wrong types
    json_str = """
    {
        "required_str": "hello",
        "required_int": "not an integer"
    }
    """
    with pytest.raises(ParseLLMJsonResponseException):
        parse_llm_json_response(json_str, model=TestModel)
