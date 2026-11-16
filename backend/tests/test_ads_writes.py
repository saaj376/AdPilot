from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.ads.googleads.client import GoogleAdsClient
from google.auth.credentials import AnonymousCredentials

import tools.google_ads_sdk_tools as tools


@pytest.fixture
def sdk(monkeypatch):
    proto_client = GoogleAdsClient(credentials=AnonymousCredentials(), developer_token="test", use_proto_plus=True)
    services = {}
    def service(name):
        return services.setdefault(name, Mock())
    client = SimpleNamespace(get_type=proto_client.get_type, enums=proto_client.enums, get_service=service)
    monkeypatch.setattr(tools, "get_client", lambda: client)
    monkeypatch.setattr(tools.settings, "GOOGLE_ADS_CUSTOMER_ID", "1234567890")
    return client


def test_keywords_actually_create_criteria(sdk):
    sdk.get_service("AdGroupService").ad_group_path.return_value = "customers/1234567890/adGroups/42"
    service = sdk.get_service("AdGroupCriterionService")
    service.mutate_ad_group_criteria.return_value.results = [SimpleNamespace(resource_name="customers/1234567890/adGroupCriteria/42~77")]
    result = tools.add_keywords.run(ad_group_id="42", keywords=[{"text": "fresh bread", "match_type": "PHRASE", "cpc": 1.25}])
    criterion = service.mutate_ad_group_criteria.call_args.kwargs["operations"][0].create
    assert criterion.keyword.text == "fresh bread"
    assert criterion.keyword.match_type == sdk.enums.KeywordMatchTypeEnum.PHRASE
    assert criterion.cpc_bid_micros == 1250000
    assert result["keyword_ids"] == ["77"]


def test_campaign_sets_bidding_and_location(sdk):
    geo = SimpleNamespace(search_term="Austin, TX", geo_target_constant=SimpleNamespace(resource_name="geoTargetConstants/1026201"))
    sdk.get_service("GeoTargetConstantService").suggest_geo_target_constants.return_value.geo_target_constant_suggestions = [geo]
    sdk.get_service("CampaignBudgetService").mutate_campaign_budgets.return_value.results = [SimpleNamespace(resource_name="customers/1234567890/campaignBudgets/1")]
    sdk.get_service("CampaignService").mutate_campaigns.return_value.results = [SimpleNamespace(resource_name="customers/1234567890/campaigns/2")]
    result = tools.create_campaign.run(name="Bakery", monthly_budget=304, geo_targets=["Austin, TX"])
    campaign = sdk.get_service("CampaignService").mutate_campaigns.call_args.kwargs["operations"][0].create
    assert campaign.status == sdk.enums.CampaignStatusEnum.PAUSED
    assert campaign._pb.HasField("manual_cpc")
    assert result["daily_budget"] == 10
    criterion = sdk.get_service("CampaignCriterionService").mutate_campaign_criteria.call_args.kwargs["operations"][0].create
    assert criterion.location.geo_target_constant == "geoTargetConstants/1026201"


def test_invalid_copy_is_rejected_before_any_write(monkeypatch):
    get_client = Mock()
    monkeypatch.setattr(tools, "get_client", get_client)
    with pytest.raises(ValueError, match="Headlines"):
        tools.create_ads.run(ad_group_id="42", headlines=["x" * 31, "Bread", "Bakery"], descriptions=["Fresh bread", "Visit our bakery"], final_url="https://bakery.example")
    get_client.assert_not_called()
