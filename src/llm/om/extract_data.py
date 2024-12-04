import anthropic
import json
import base64
from typing import Dict, Any
from io import BytesIO
import shutil
import os
from tenacity import retry, stop_after_attempt, wait_exponential
from src.database.models.om_data_extract import UnitType, RentRoll, Expenses
from src.llm.utils.json_helpers import parse_llm_json_response
from pydantic import BaseModel
from typing import BinaryIO

UNIT_TYPES = ", ".join(UnitType.__members__.values())

RENT_ROLL_EXAMPLE = [
    RentRoll(
        unit="1",
        unit_type=UnitType.OFFICE,
        rent_stabilized=True,
        square_feet=15000,
        lease_expiration="2032-01-01",
        monthly_inplace_rent=15000,
        annual_inplace_rent=180000,
        monthly_projected_rent=16000,
        annual_projected_rent=192000,
    ),
    RentRoll(
        unit="2",
        unit_type=UnitType.ONE_BR,
        rent_stabilized=False,
        square_feet=700,
        lease_expiration=None,
        monthly_inplace_rent=None,
        annual_inplace_rent=None,
        monthly_projected_rent=1200,
        annual_projected_rent=14400,
    ),
    RentRoll(
        unit="3",
        unit_type=UnitType.TWO_BR,
        rent_stabilized=True,
        square_feet=900,
        lease_expiration="2032-01-01",
        monthly_inplace_rent=1200,
        annual_inplace_rent=14400,  
        monthly_projected_rent=1300,
        annual_projected_rent=15600,
    )
]

EXPENSES_EXAMPLE = Expenses(
    in_place_income=1800000,
    in_place_expenses={"property_taxes": 300000, "insurance": 20000, "maintenance": 10000},
    projected_income=1920000,
    projected_expenses={"property_taxes": 320000, "insurance": 22000, "maintenance": 11000}
)

ANALYSIS_EXAMPLE = json.dumps({
    "rent_roll": [rent_roll.model_dump_json() for rent_roll in RENT_ROLL_EXAMPLE],
    "expenses": EXPENSES_EXAMPLE.model_dump_json()
}, indent=2)


def check_poppler_installed() -> bool:
    """Check if poppler is installed and accessible"""
    return shutil.which('pdftoppm') is not None

def convert_to_images(pdf_stream: BinaryIO) -> list[str]:
    """
    Convert PDF to base64 encoded images from a binary stream.
    
    Args:
        pdf_stream: File-like object in binary mode (from open() or MinIO)
    """
    if not check_poppler_installed():
        raise RuntimeError("Poppler is required but not installed...")
    
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise ImportError("Required packages not installed...")

    try:
        # Ensure we're at the start of the stream
        pdf_stream.seek(0)
        
        # Read the entire stream
        pdf_data = pdf_stream.read()
        if not pdf_data:
            raise ValueError("PDF stream is empty")
            
        images = convert_from_bytes(pdf_data)
        
        # Convert images to base64
        base64_images = []
        for img in images:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            base64_images.append(img_base64)
        
        return base64_images

    except Exception as e:
        raise RuntimeError(f"Failed to convert PDF: {str(e)}") from e

def clean_json_response(text: str) -> str:
    """Clean and prepare JSON string for parsing"""
    # Extract JSON portion
    start = text.find('{')
    end = text.rfind('}') + 1
    if start >= 0 and end > 0:
        text = text[start:end]
    
    # For CSV fields, wrap the entire multi-line string in triple quotes
    for csv_field in ["rent_roll", "financials", "market_metrics"]:
        field_start = text.find(f'"{csv_field}": "')
        if field_start != -1:
            # Find the end of the CSV string (last quote before the next comma or })
            field_end = text.find('",', field_start)
            if field_end == -1:  # might be the last field
                field_end = text.find('"}', field_start)
            
            if field_end != -1:
                # Extract the CSV content
                csv_content = text[field_start:field_end + 1]
                # Replace with properly closed triple-quoted version
                text = text.replace(
                    csv_content, 
                    csv_content.replace('": "', '": """', 1).replace(
                        '",', '""",', 1
                    ).replace('"}', '"""}', 1)
                )
    
    return text

class PropertyAnalysis(BaseModel):
    """Model for property analysis response"""
    rent_roll: list[RentRoll]
    expenses: Expenses

# TODO: make this screen over relevant text too, not just images
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def screen_page(anthropic_client: anthropic.Client, image_base64: str) -> bool:
    """Screen a single page for relevant data."""
    screening_prompt = """Examine this page for
    - tables, diagrams, or numerical data
    - rent roll information (units, square footage, rents)
    - financial data (income, expenses, operating statements)
Respond with EXACTLY one word: either 'RELEVANT' or 'IRRELEVANT'.
No explanation needed."""
    
    response = anthropic_client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=10,  # Reduced significantly
        temperature=0,  # Added to ensure consistent responses
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": screening_prompt},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_base64
                    }
                }
            ]
        }]
    )

    not_relevant = 'IRRELEVANT' in response.content[0].text.upper()
    relevant = 'RELEVANT' in response.content[0].text.upper()

    ret = (not not_relevant) and relevant
    return ret
    
@retry(
# TODO: should maybe pass along text if relevant
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def extract_data(anthropic_client: anthropic.Client, pdf_stream: BinaryIO) -> PropertyAnalysis:
    """
    Analyze property document and return structured data.
    """
    base64_images = convert_to_images(pdf_stream)
    
    # First pass: screen pages for relevance
    i = 0
    relevant_images = []
    for img_base64 in base64_images:
        i += 1
        if screen_page(anthropic_client, img_base64):
            print(f"relevant page {i}")
            relevant_images.append(img_base64)
    
    if len(relevant_images) == 0:
        raise ValueError("No relevant pages found in document")

    # Simplifiedtracting,on prompt focusing only on thet.structure
    extraction_prompt = """Extract ALL data from the provided images into JSON format. For large tables:
1. Process the table row by row systematically
2. Double-check that all rows are included in your response
3. Verify the total number of units matches the property total

Extract the following data:
1. Rent roll details (units, square footage, rents)
2. Financial details (income and expenses)

Provide your response in JSON format such as the following example:

{analysis_example}

Important:
- Process ALL rows in any tables, even if they are lengthy
- Verify row counts match totals shown
- Currency values: integer only
- Square footage: integer only
- Dates: YYYY-MM-DD or null if not applicable
- Missing values must be null
- Unit types must be one of: {unit_types}
"""
    prompt_text = extraction_prompt.format(
        analysis_example=ANALYSIS_EXAMPLE, 
        unit_types=UNIT_TYPES
    )
    # Prepare content with only relevant pages
    content = [{"type": "text", "text": prompt_text}]

    print(f"extracting from {len(relevant_images)} pages")
    print(f"prompt: {prompt_text}")
    
    for img_base64 in relevant_images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": img_base64
            }
        })

    # Consider breaking up large tables into chunks
    max_tokens = 4000
    if len(relevant_images) > 1:
        max_tokens = 8000  # Increase token limit for multiple pages

    response = anthropic_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=max_tokens,  # Increased token limit
        temperature=0,  # Added to ensure consistent responses
        messages=[{
            "role": "user", 
            "content": content
        }]
    )

    print(f"response: {response.content[0].text}")
    
    # Extract and parse response
    content = response.content[0]
    if not hasattr(content, "text"):
        raise ValueError("Unexpected response format from Anthropic API")
    try:
        return parse_llm_json_response(
            response_text=content.text,
            model=PropertyAnalysis
        )
    except Exception as e:
        raise ValueError(f"Failed to parse JSON response: {str(e)}") from e
