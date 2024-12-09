from io import BytesIO
import json
from pathlib import Path

import anthropic
import pytest

from src.llm.engines.om.engine import OmEngine
from src.config import Config

# Get the absolute path to the fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"

# @pytest.mark.slow
async def test_process_pdf_20_w_37_st():
    pdf_path = FIXTURES_DIR / "20_w_37_st.pdf"
    config = Config()
    anthropic_client = anthropic.Client(api_key=config.secrets.anthropic_api_key)
    engine = OmEngine(anthropic_client)
    
    try:
        print(f"Opening {pdf_path}...")
        with open(pdf_path, "rb") as pdf_file:
            pdf_stream = BytesIO(pdf_file.read())
            context = await engine.process_pdf(pdf_stream)

        # pretty print the context
        print(json.dumps(context, default=str, indent=4))

        # Test metadata extraction
        assert context.title is not None
        assert context.address is not None
        assert context.description is not None
        assert context.running_summary != ""
        assert context.property_type is not None
        assert context.square_feet is not None
        assert context.total_units is not None

        # Do a fuzzy match on 'rent roll table'
        assert any("rent roll" in table_type for table_type in context.tables)
        rent_roll = context.tables["rent_roll"]
        assert len(rent_roll) == 12

    except Exception as e:
        print(f"Unexpected error in process_pdf: {e}")
        raise