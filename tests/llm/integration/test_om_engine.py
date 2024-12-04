from datetime import date
from io import BytesIO
from pathlib import Path

import anthropic
import pytest

from src.database.models.om_data_extract import UnitType
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

        print(context)

        # Test metadata extraction
        assert context.title is not None
        assert context.address is not None
        assert context.description is not None
        assert context.running_summary != ""

        # # Test table extraction
        # assert "rent_roll" in context.tables
        # rent_roll = context.tables["rent_roll"]
        # assert len(rent_roll) == 12

        # # Check specific entries
        # first_unit = rent_roll[0]
        # assert first_unit["unit_type"] == UnitType.RETAIL
        # assert first_unit["rent_stabilized"] in [None, False]
        # assert first_unit["square_feet"] == 10250
        # assert first_unit["lease_expiration"] is None
        # assert first_unit["monthly_inplace_rent"] is None
        # assert first_unit["annual_inplace_rent"] is None
        # assert first_unit["monthly_projected_rent"] == 76875
        # assert first_unit["annual_projected_rent"] == 922500

        # sixth_unit = rent_roll[5]
        # assert sixth_unit["unit_type"] == UnitType.OFFICE
        # assert sixth_unit["rent_stabilized"] in [None, False]
        # assert sixth_unit["square_feet"] == 6500
        # assert sixth_unit["lease_expiration"] == date(2026, 1, 31)
        # assert sixth_unit["monthly_inplace_rent"] == 18000
        # assert sixth_unit["annual_inplace_rent"] == 215995
        # assert sixth_unit["monthly_projected_rent"] == 18000
        # assert sixth_unit["annual_projected_rent"] == 215995

    except Exception as e:
        print(f"Unexpected error in process_pdf: {e}")
        raise

@pytest.mark.slow
async def test_process_pdf_1004_gates_ave():
    pdf_path = FIXTURES_DIR / "1004_gates_ave.pdf"
    config = Config()
    anthropic_client = anthropic.Client(api_key=config.secrets.anthropic_api_key)
    engine = OmEngine(anthropic_client)
    
    try:
        with open(pdf_path, "rb") as pdf_file:
            pdf_stream = BytesIO(pdf_file.read())
            context = await engine.process_pdf(pdf_stream)

        print(context)

        # Test metadata extraction
        assert context.title is not None
        assert context.address is not None
        assert context.description is not None
        assert context.running_summary != ""

        # # Test table extraction
        # assert "rent_roll" in context.tables
        # rent_roll = context.tables["rent_roll"]
        # assert len(rent_roll) == 27

        # # Check specific entries
        # first_unit = rent_roll[0]
        # assert first_unit["unit"] == "1A"
        # assert first_unit["unit_type"] == UnitType.ONE_BR
        # assert first_unit["rent_stabilized"] is True
        # assert first_unit["square_feet"] == 408
        # assert first_unit["lease_expiration"] is None
        # assert first_unit["monthly_inplace_rent"] == 2600
        # assert first_unit["annual_inplace_rent"] == 31200
        # assert first_unit["monthly_projected_rent"] is None
        # assert first_unit["annual_projected_rent"] is None

        # sixth_unit = rent_roll[5]
        # assert sixth_unit["unit_type"] == UnitType.TWO_BR
        # assert sixth_unit["rent_stabilized"] is True
        # assert sixth_unit["square_feet"] == 477
        # assert sixth_unit["lease_expiration"] == date(2025, 1, 31)
        # assert sixth_unit["monthly_inplace_rent"] == 2478
        # assert sixth_unit["annual_inplace_rent"] == 29736
        # assert sixth_unit["monthly_projected_rent"] is None
        # assert sixth_unit["annual_projected_rent"] is None

    except Exception as e:
        print(f"Unexpected error in process_pdf: {e}")
        raise
