from enum import Enum as PyEnum

class LLMExceptionType(PyEnum):
    invalid_response = "invalid_response"

class LLMException(Exception):
    def __init__(self, type: LLMExceptionType, message: str):
        self.message = message
        self.type = type
