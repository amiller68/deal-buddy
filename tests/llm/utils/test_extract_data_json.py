from src.database.models.om_data_extract import UnitType 
from src.llm.utils.json_helpers import parse_llm_json_response
from src.llm.om.extract_data import PropertyAnalysis

def test_property_analysis_model():
    # Test valid property analysis JSON
    json_str = """
    {
        "rent_roll": [
            {
                "unit": "1",
                "unit_type": "office",
                "rent_stabilized": true,
                "square_feet": 15000,
                "lease_expiration": "2032-01-01",
                "monthly_inplace_rent": 15000,
                "annual_inplace_rent": 180000
            }
        ],
        "expenses": {
            "in_place_income": 1800000,
            "in_place_expenses": {
                "property_taxes": 300000,
                "insurance": 20000
            },
            "projected_income": 1920000,
            "projected_expenses": {
                "property_taxes": 320000,
                "insurance": 22000
            }
        }
    }
    """
    result = parse_llm_json_response(json_str, model=PropertyAnalysis)
    assert isinstance(result, PropertyAnalysis)
    assert len(result.rent_roll) == 1
    assert result.rent_roll[0].unit == "1"
    assert result.rent_roll[0].unit_type == UnitType.OFFICE
    assert result.expenses.in_place_income == 1800000

def test_property_analysis_with_optional_fields():
    # Test JSON with minimal required fields
    json_str = """
    {
        "rent_roll": [
            {
                "unit": "1",
                "unit_type": "office",
                "rent_stabilized": true,
                "square_feet": 15000
            }
        ],
        "expenses": {
            "in_place_income": 1800000,
            "in_place_expenses": {},
            "projected_income": 1920000,
            "projected_expenses": {}
        }
    }
    """
    result = parse_llm_json_response(json_str, model=PropertyAnalysis)
    assert isinstance(result, PropertyAnalysis)
    assert result.rent_roll[0].lease_expiration is None
    assert result.rent_roll[0].monthly_inplace_rent is None