from crewai import tool
from google.ads.googleads.errors import GoogleAdsException

from config import settings
from services.google_ads_client import get_client, handle_google_ads_error


# All the write operations for Google Ads live here.
# These are the @tool functions used by:
#   - KeywordAgent  → get_keyword_ideas
#   - LaunchAgent   → create_campaign, create_ad_group, create_ads
#   - OptimizeAgent → update_keyword_bid, pause_keyword, reallocate_budget
#
# Each function:
#   1. Gets the SDK client (the connection we set up in google_ads_client.py)
#   2. Makes the real API call to Google Ads
#   3. Returns a plain dict so the agent can read the result easily
#   4. Catches any Google Ads errors and returns a readable message
#      instead of crashing the whole pipeline


# ─── KeywordAgent ─────────────────────────────────────────────────────────────

@tool("Get keyword ideas")
def get_keyword_ideas(seed_keywords: list[str], location: str) -> list[dict]:
    """
    Calls Google Keyword Planner and returns keyword suggestions.
    Each keyword comes with monthly search volume and average CPC.
    KeywordAgent uses this to build the keyword strategy.

    Args:
        seed_keywords: starting keywords e.g. ["pizza austin", "italian food"]
        location:      target location e.g. "Austin, TX"

    Returns:
        List of dicts with text, avg_monthly_searches, cpc, competition
    """
    try:
        client = get_client()
        keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")

        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = settings.GOOGLE_ADS_CUSTOMER_ID
        request.language = "languageConstants/1000"   # English
        request.include_adult_keywords = False

        # Default to United States geo target
        request.geo_target_constants.append("geoTargetConstants/2840")

        # Add the seed keywords the agent provides
        request.keyword_seed.keywords.extend(seed_keywords)

        response = keyword_plan_idea_service.generate_keyword_ideas(
            request=request
        )

        results = []
        for idea in response:
            metrics = idea.keyword_idea_metrics
            results.append({
                "text":                 idea.text,
                "avg_monthly_searches": metrics.avg_monthly_searches,
                # Google stores CPC in micros (millionths of a dollar) — convert to USD
                "cpc":                  metrics.average_cpc_micros / 1_000_000,
                "competition":          str(metrics.competition.name),
            })

        return results

    except GoogleAdsException as ex:
        # Return error as a list item so agent gets a consistent return type
        return [{"error": handle_google_ads_error(ex)}]


# ─── LaunchAgent ──────────────────────────────────────────────────────────────

@tool("Create campaign")
def create_campaign(name: str, monthly_budget: float, geo_targets: list[str]) -> dict:
    """
    Creates a new Google Ads Search campaign and its budget.
    LaunchAgent calls this first — the campaign_id it returns
    is needed by create_ad_group.

    The campaign starts as PAUSED — safe default so no money
    is spent until everything is reviewed and ready.

    Args:
        name:           campaign name e.g. "Tony's Pizza — Austin"
        monthly_budget: total monthly spend in USD e.g. 1500.0
        geo_targets:    list of location strings e.g. ["Austin, TX"]

    Returns:
        Dict with campaign_id, name, status, daily_budget
    """
    try:
        client = get_client()
        customer_id = settings.GOOGLE_ADS_CUSTOMER_ID

        campaign_budget_service = client.get_service("CampaignBudgetService")
        campaign_service = client.get_service("CampaignService")

        # Step 1 — create the budget first
        # Google Ads works with daily budgets internally
        # Users think in monthly so we divide by 30
        # Google stores money in micros (1 USD = 1,000,000 micros)
        daily_budget_micros = int((monthly_budget / 30) * 1_000_000)

        budget_op = client.get_type("CampaignBudgetOperation")
        budget = budget_op.create
        budget.name = f"{name} Budget"
        budget.amount_micros = daily_budget_micros
        budget.delivery_method = (
            client.enums.BudgetDeliveryMethodEnum.STANDARD
        )

        budget_response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=customer_id, operations=[budget_op]
        )
        budget_resource = budget_response.results[0].resource_name

        # Step 2 — create the campaign and attach the budget to it
        campaign_op = client.get_type("CampaignOperation")
        campaign = campaign_op.create
        campaign.name = name
        campaign.status = client.enums.CampaignStatusEnum.PAUSED
        campaign.advertising_channel_type = (
            client.enums.AdvertisingChannelTypeEnum.SEARCH
        )
        campaign.campaign_budget = budget_resource
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = True

        campaign_response = campaign_service.mutate_campaigns(
            customer_id=customer_id, operations=[campaign_op]
        )

        # Resource names look like "customers/1234567890/campaigns/9876543210"
        # We split on "/" and take the last part to get just the numeric ID
        campaign_resource = campaign_response.results[0].resource_name
        campaign_id = campaign_resource.split("/")[-1]

        return {
            "campaign_id":   campaign_id,
            "campaign_name": name,
            "status":        "PAUSED",
            "daily_budget":  monthly_budget / 30,
            "resource_name": campaign_resource,
        }

    except GoogleAdsException as ex:
        return {"error": handle_google_ads_error(ex)}


@tool("Create ad group")
def create_ad_group(campaign_id: str, name: str) -> dict:
    """
    Creates an ad group inside an existing campaign.
    Ad groups are theme buckets — LaunchAgent creates one
    per theme (e.g. "Dine In", "Delivery", "Catering").
    Keywords and ads are added to ad groups, not campaigns directly.

    Args:
        campaign_id: the ID returned by create_campaign
        name:        ad group name e.g. "Dine In"

    Returns:
        Dict with ad_group_id, name, campaign_id
    """
    try:
        client = get_client()
        customer_id = settings.GOOGLE_ADS_CUSTOMER_ID

        ad_group_service = client.get_service("AdGroupService")

        # Build the full campaign resource name Google expects
        campaign_resource = client.get_service(
            "CampaignService"
        ).campaign_path(customer_id, campaign_id)

        ad_group_op = client.get_type("AdGroupOperation")
        ad_group = ad_group_op.create
        ad_group.name = name
        ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
        ad_group.campaign = campaign_resource
        ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ad_group.cpc_bid_micros = 1_000_000   # default $1.00 CPC — OptimizeAgent adjusts later

        response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id, operations=[ad_group_op]
        )

        resource_name = response.results[0].resource_name
        ad_group_id = resource_name.split("/")[-1]

        return {
            "ad_group_id":   ad_group_id,
            "name":          name,
            "campaign_id":   campaign_id,
            "resource_name": resource_name,
        }

    except GoogleAdsException as ex:
        return {"error": handle_google_ads_error(ex)}


@tool("Create responsive search ads")
def create_ads(
    ad_group_id: str,
    headlines: list[str],
    descriptions: list[str],
    final_url: str
) -> dict:
    """
    Creates a Responsive Search Ad inside an ad group.
    Google mixes and matches the headlines and descriptions
    automatically to find the best performing combinations.
    Headlines come from CreativeAgent, ad_group_id from LaunchAgent.

    Args:
        ad_group_id:  the ID returned by create_ad_group
        headlines:    3 to 15 headlines, max 30 chars each
        descriptions: 2 to 4 descriptions, max 90 chars each
        final_url:    the landing page URL e.g. "https://tonypizza.com"

    Returns:
        Dict with ad_id and status
    """
    try:
        client = get_client()
        customer_id = settings.GOOGLE_ADS_CUSTOMER_ID

        ad_group_ad_service = client.get_service("AdGroupAdService")

        ad_group_resource = client.get_service(
            "AdGroupService"
        ).ad_group_path(customer_id, ad_group_id)

        ad_group_ad_op = client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_group_ad_op.create
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED
        ad_group_ad.ad_group = ad_group_resource

        ad = ad_group_ad.ad
        ad.final_urls.append(final_url)

        # Add headlines — Google requires at least 3, max 15
        for headline_text in headlines[:15]:
            headline = client.get_type("AdTextAsset")
            headline.text = headline_text[:30]  # silently trim to Google's 30 char limit
            ad.responsive_search_ad.headlines.append(headline)

        # Add descriptions — Google requires at least 2, max 4
        for desc_text in descriptions[:4]:
            description = client.get_type("AdTextAsset")
            description.text = desc_text[:90]  # silently trim to Google's 90 char limit
            ad.responsive_search_ad.descriptions.append(description)

        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=customer_id, operations=[ad_group_ad_op]
        )

        resource_name = response.results[0].resource_name
        ad_id = resource_name.split("/")[-1]

        return {
            "ad_id":         ad_id,
            "ad_group_id":   ad_group_id,
            "status":        "ENABLED",
            "resource_name": resource_name,
        }

    except GoogleAdsException as ex:
        return {"error": handle_google_ads_error(ex)}


# ─── OptimizeAgent ────────────────────────────────────────────────────────────

@tool("Update keyword bid")
def update_keyword_bid(ad_group_id: str, keyword_id: str, new_bid_usd: float) -> dict:
    """
    Updates the CPC bid for a specific keyword.
    OptimizeAgent calls this for keywords performing well
    and deserving a higher bid to win more impressions.

    Args:
        ad_group_id:  the ad group the keyword lives in
        keyword_id:   the keyword's numeric ID
        new_bid_usd:  new CPC bid in USD e.g. 2.50

    Returns:
        Dict with keyword_id, new_bid, status
    """
    try:
        client = get_client()
        customer_id = settings.GOOGLE_ADS_CUSTOMER_ID

        ad_group_criterion_service = client.get_service(
            "AdGroupCriterionService"
        )

        keyword_resource = ad_group_criterion_service.ad_group_criterion_path(
            customer_id, ad_group_id, keyword_id
        )

        criterion_op = client.get_type("AdGroupCriterionOperation")
        criterion = criterion_op.update
        criterion.resource_name = keyword_resource
        # Convert USD to micros — Google stores all money as micros
        criterion.cpc_bid_micros = int(new_bid_usd * 1_000_000)

        ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=customer_id, operations=[criterion_op]
        )

        return {
            "keyword_id": keyword_id,
            "new_bid":    new_bid_usd,
            "status":     "UPDATED",
        }

    except GoogleAdsException as ex:
        return {"error": handle_google_ads_error(ex)}


@tool("Pause keyword")
def pause_keyword(ad_group_id: str, keyword_id: str) -> dict:
    """
    Pauses an underperforming keyword so it stops spending budget.
    OptimizeAgent calls this for keywords with low CTR or
    high cost relative to conversions.
    The keyword stays in the system — it can be re-enabled later.

    Args:
        ad_group_id: the ad group the keyword lives in
        keyword_id:  the keyword's numeric ID

    Returns:
        Dict with keyword_id and status
    """
    try:
        client = get_client()
        customer_id = settings.GOOGLE_ADS_CUSTOMER_ID

        ad_group_criterion_service = client.get_service(
            "AdGroupCriterionService"
        )

        keyword_resource = ad_group_criterion_service.ad_group_criterion_path(
            customer_id, ad_group_id, keyword_id
        )

        criterion_op = client.get_type("AdGroupCriterionOperation")
        criterion = criterion_op.update
        criterion.resource_name = keyword_resource
        criterion.status = client.enums.AdGroupCriterionStatusEnum.PAUSED

        ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=customer_id, operations=[criterion_op]
        )

        return {
            "keyword_id": keyword_id,
            "status":     "PAUSED",
        }

    except GoogleAdsException as ex:
        return {"error": handle_google_ads_error(ex)}


@tool("Reallocate campaign budget")
def reallocate_budget(campaign_id: str, new_monthly_budget: float) -> dict:
    """
    Updates the daily budget cap for a campaign.
    OptimizeAgent calls this when the campaign is performing
    well and could benefit from more spend — or needs to cut back.

    Args:
        campaign_id:        the campaign's numeric ID
        new_monthly_budget: new monthly budget in USD e.g. 2000.0

    Returns:
        Dict with campaign_id, new_daily_budget, status
    """
    try:
        client = get_client()
        customer_id = settings.GOOGLE_ADS_CUSTOMER_ID

        campaign_budget_service = client.get_service("CampaignBudgetService")
        ga_service = client.get_service("GoogleAdsService")

        # First fetch the campaign to find its budget resource name
        query = f"""
            SELECT campaign.id, campaign_budget.resource_name
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """
        response = ga_service.search(customer_id=customer_id, query=query)
        row = next(iter(response))
        budget_resource = row.campaign_budget.resource_name

        # Update the budget
        new_daily_micros = int((new_monthly_budget / 30) * 1_000_000)

        budget_op = client.get_type("CampaignBudgetOperation")
        budget = budget_op.update
        budget.resource_name = budget_resource
        budget.amount_micros = new_daily_micros

        campaign_budget_service.mutate_campaign_budgets(
            customer_id=customer_id, operations=[budget_op]
        )

        return {
            "campaign_id":      campaign_id,
            "new_daily_budget": new_monthly_budget / 30,
            "status":           "UPDATED",
        }

    except GoogleAdsException as ex:
        return {"error": handle_google_ads_error(ex)}