from enum import Enum
import json
import logging
from typing import Dict, Any, Type, TypeVar, Union, List, Optional
from pydantic import BaseModel, ValidationError

T = TypeVar('T', bound=BaseModel)

class ParseLLMJsonResponseErrorType(str, Enum):
    # target text is just text, not json
    NOT_JSON = "NOT_JSON"
    # error decoding json
    JSON_DECODE_ERROR = "JSON_DECODE_ERROR"
    # error validating against pydantic model
    VALIDATION_ERROR = "VALIDATION_ERROR"

class ParseLLMJsonResponseException(Exception):
    """Exception raised for errors in parsing LLM JSON response"""

    def __init__(self, message: str, error_type: ParseLLMJsonResponseErrorType):
        self.message = message
        self.error_type = error_type

def parse_llm_json_response(
    response_text: str, 
    model: Optional[Type[T]] = None,
    keys: Optional[list[str]] = None,
) -> Union[T, Dict[str, Any], List[Dict[str, Any]]]:
    """
    Parses JSON response from LLM, optionally validating against a Pydantic model
    or checking for required keys. Can extract JSON from within regular text.
    
    Args:
        response_text: Raw response text from LLM
        model_or_keys: Optional Pydantic model class or list of required keys
    
    Returns:
        If model is provided: Validated Pydantic model instance
        If keys are provided or None: Dict or List of dicts from JSON
    """
    # Try to extract JSON content from the text
    try:
        # First try to parse the entire text as JSON
        raw_data = json.loads(response_text.strip())
    except json.JSONDecodeError:
        print(f"failed to parse entire text as JSON: {response_text}")
        # If that fails, try to find JSON between curly braces
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_text = response_text[start_idx:end_idx + 1].strip()
            print(f"json_text: {json_text}")
            try:
                raw_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                raise ParseLLMJsonResponseException(
                    message=f"Failed to decode JSON response: {e}",
                    error_type=ParseLLMJsonResponseErrorType.JSON_DECODE_ERROR
                )
        else:
            raise ParseLLMJsonResponseException(
                message="No JSON content found in response",
                error_type=ParseLLMJsonResponseErrorType.NOT_JSON
            )

    print(f"raw_data: {raw_data}")

    if model is None and keys is None:
        return raw_data

    # If we got a list of keys, validate those keys exist
    if keys is not None:
        missing_keys = [key for key in keys if key not in raw_data]
        if missing_keys:
            raise ParseLLMJsonResponseException(
                message=f"Missing required keys in response: {missing_keys}",
                error_type=ParseLLMJsonResponseErrorType.VALIDATION_ERROR
            )
        return raw_data

    # Otherwise, validate against Pydantic model
    try:
        return model.model_validate(raw_data)
    except ValidationError as e:
        raise ParseLLMJsonResponseException(
            message=f"Validation failed: {e}",
            error_type=ParseLLMJsonResponseErrorType.VALIDATION_ERROR
        )
