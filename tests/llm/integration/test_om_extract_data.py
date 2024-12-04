from datetime import datetime
from io import BytesIO
from pathlib import Path
from datetime import date, datetime

import anthropic
import pytest

from src.database.models.om_data_extract import RentRoll, UnitType
from src.llm.om.extract_data import PropertyAnalysis, extract_data
from src.config import Config

# Get the absolute path to the fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"

@pytest.mark.slow
def test_extract_data():
    pdf_path = FIXTURES_DIR / "20_w_37_st.pdf"
    config = Config()
    anthropic_client = anthropic.Client(api_key=config.secrets.anthropic_api_key)
    try:
        print(f"Opening {pdf_path}...")
        with open(pdf_path, "rb") as pdf_file:
            pdf_stream = BytesIO(pdf_file.read())
            response = extract_data(anthropic_client, pdf_stream)

        assert isinstance(response, PropertyAnalysis)
        assert response.rent_roll is not None
        assert response.expenses is not None

        # Assuming we extract in order
        rent_roll = response.rent_roll
        assert len(rent_roll) == 12
        # check out the 1st and 6th rent rolls
        # NOTE: dont do this check since its kinda random
        # assert rent_rolls[0].unit == "1"
        assert rent_roll[0].unit_type == UnitType.RETAIL
        # either None or False
        assert rent_roll[0].rent_stabilized in [None, False]
        assert rent_roll[0].square_feet == 10250
        assert rent_roll[0].lease_expiration == None
        assert rent_roll[0].monthly_inplace_rent == None
        assert rent_roll[0].annual_inplace_rent == None
        assert rent_roll[0].rent_stabalized_inplace_monthly_rent == None
        assert rent_roll[0].rent_stabalized_inplace_annual_rent == None
        assert rent_roll[0].monthly_projected_rent == 76875
        assert rent_roll[0].annual_projected_rent == 922500
        assert rent_roll[0].rent_stabalized_projected_monthly_rent == None
        assert rent_roll[0].rent_stabalized_projected_annual_rent == None

        # assert rent_rols[5].unit == "6"
        assert rent_roll[5].unit_type == UnitType.OFFICE
        assert rent_roll[5].rent_stabilized in [None, False]
        assert rent_roll[5].square_feet == 6500
        assert rent_roll[5].lease_expiration == date(2026, 1, 31)
        # NOTE: these dot match up
        assert rent_roll[5].monthly_inplace_rent == 18000
        assert rent_roll[5].annual_inplace_rent == 215995
        assert rent_roll[5].rent_stabalized_inplace_monthly_rent == None
        assert rent_roll[5].rent_stabalized_inplace_annual_rent == None
        assert rent_roll[5].monthly_projected_rent == 18000
        assert rent_roll[5].annual_projected_rent == 215995
        assert rent_roll[5].rent_stabalized_projected_monthly_rent == None
        assert rent_roll[5].rent_stabalized_projected_annual_rent == None



    except Exception as e:
        print(f"Unexpected error in extract_data: {e}")
        raise

@pytest.mark.slow
def test_extract_data_1004_gates_ave():
    pdf_path = FIXTURES_DIR / "1004_gates_ave.pdf"
    config = Config()
    anthropic_client = anthropic.Client(api_key=config.secrets.anthropic_api_key)
    try:
        with open(pdf_path, "rb") as pdf_file:
            pdf_stream = BytesIO(pdf_file.read())
            response = extract_data(anthropic_client, pdf_stream)

        assert isinstance(response, PropertyAnalysis)
        assert response.rent_roll is not None
        assert response.expenses is not None

        rent_roll = response.rent_roll
        assert len(rent_roll) == 27
        # check out the 1st and 6th rent rolls
        # NOTE: dont do this check since its kinda random
        assert rent_roll[0].unit == "1A"
        assert rent_roll[0].unit_type == UnitType.ONE_BR
        # should be true
        assert rent_roll[0].rent_stabilized is True
        assert rent_roll[0].square_feet == 408
        assert rent_roll[0].lease_expiration == None
        assert rent_roll[0].monthly_inplace_rent == 2600
        assert rent_roll[0].annual_inplace_rent == 31200
        assert rent_roll[0].monthly_projected_rent == None
        assert rent_roll[0].annual_projected_rent == None

        # assert rent_rols[5].unit == "6"
        assert rent_roll[5].unit_type == UnitType.TWO_BR
        assert rent_roll[5].rent_stabilized is True
        assert rent_roll[5].square_feet == 477
        assert rent_roll[5].lease_expiration == date(2025, 1, 31)
        # NOTE: these dot match up
        assert rent_roll[5].monthly_inplace_rent == 2478
        assert rent_roll[5].annual_inplace_rent == 29736
        assert rent_roll[5].monthly_projected_rent == None
        assert rent_roll[5].annual_projected_rent == None



    except Exception as e:
        print(f"Unexpected error in extract_data: {e}")
        raise
