import pytest


@pytest.fixture
def campaign_payload() -> dict:
	return {
		"business_description": "A family owned pizza restaurant in Austin with delivery and dine-in.",
		"monthly_budget": 1000.0,
		"geo_targets": ["Austin, TX"],
	}
