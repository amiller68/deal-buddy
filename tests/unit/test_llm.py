from io import BytesIO
from pathlib import Path

import anthropic

from src.utils import extract_text_from_pdf_stream
from src.llm.om import generate_summary
from src.config import Config

# Get the absolute path to the fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_generate_summary():
    # Open the sample PDF file
    pdf_path = FIXTURES_DIR / "om.pdf"
    config = Config()
    anthropic_client = anthropic.Client(api_key=config.secrets.anthropic_api_key)

    with open(pdf_path, "rb") as pdf_file:
        # Create a BytesIO object from the PDF file
        pdf_stream = BytesIO(pdf_file.read())

        # Extract text from the PDF
        extracted_text = extract_text_from_pdf_stream(pdf_stream)

        print(extracted_text)

        summary = generate_summary(anthropic_client, extracted_text)

        assert isinstance(summary, dict)
        assert summary['address'] is not None
        assert summary['title'] is not None
        assert summary['description'] is not None
        assert summary['summary'] is not None

        # assert "Expected Text" in extracted_text