import anthropic
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.llm import LLMException, LLMExceptionType

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((ValueError, json.JSONDecodeError)),
    reraise=True
)
async def generate_summary(
        anthropic_client: anthropic.Client,
        pdf_text: str
) -> str:
    prompt = """You are a real estate expert. Analyze the following real estate deal information and provide three sections:

1. Title: Either the property address or a short descriptor of the property (1 line)
2. Description: A short description of the property that can fit in a blurb (2-3 sentences)
3. Summary: A 500-1000 word summary of the key features and relevant extractable data from the offering memorandum, including:
   - Property type and location
   - Size and key features
   - Current occupancy and major tenants
   - Financial highlights (e.g., asking price, NOI, cap rate)
   - Unique selling points or challenges
   - Market analysis
   - Investment highlights
   - Any other relevant information

Here's the text to analyze:

{pdf_text}

Provide your response in JSON format with keys "title", "description", and "summary".
"""

    try:
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt.format(pdf_text=pdf_text)}],
        )

        # Parse the JSON response
        result = response.content[0].text.strip()

        # # Ensure all required keys are present
        # required_keys = ["title", "description", "summary"]
        # for key in required_keys:
        #     if key not in result:
        #         raise ValueError(f"Missing required key in response: {key}")

        # return json.dumps(result)
        return result
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        raise
    except ValueError as e:
        print(f"Value error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error in generate_summary: {e}")
        raise