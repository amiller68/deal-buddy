from io import BytesIO
from pathlib import Path

from src.utils import extract_text_from_pdf_stream

# Get the absolute path to the fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_extract_text_from_pdf():
    # Open the sample PDF file
    pdf_path = FIXTURES_DIR / "om.pdf"

    with open(pdf_path, "rb") as pdf_file:
        # Create a BytesIO object from the PDF file
        pdf_stream = BytesIO(pdf_file.read())

        # Extract text from the PDF
        extracted_text = extract_text_from_pdf_stream(pdf_stream)

        # Basic assertions
        assert isinstance(extracted_text, str)
        assert len(extracted_text) > 0
        # Add more specific assertions based on your sample PDF content
        # assert "Expected Text" in extracted_text
