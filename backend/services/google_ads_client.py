from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from config import settings

_client: GoogleAdsClient | None = None

def get_client() -> GoogleAdsClient:
    """
    Returns the Google Ads SDK client.
 
    Think of this like opening a connection to Google Ads —
    we open it once when first needed, then keep it open.
    All @tool functions (create_campaign, update_bid etc.)
    call this at the start to get the connection.
    """
    global _client
    if _client is None:
        # load_from_dict reads our credentials from settings
        # settings.google_ads_sdk_config is the property in config.py
        # that assembles the dict from all the GOOGLE_ADS_* env vars
        _client = GoogleAdsClient.load_from_dict(
            settings.google_ads_sdk_config,
            version="v18",   # current stable Google Ads API version
        )
    return _client

def check_sdk_credentials() -> None:
    """
    Runs at server startup to make sure all 5 credentials are filled in.
 
    We check credentials are present without actually calling Google —
    a live test would be slow on every startup and would fail during
    development before you have real credentials.
    If anything is missing, you get a clear list of exactly what to add
    to your .env instead of a cryptic error later mid-pipeline.
    """
    required = {
        "GOOGLE_ADS_DEVELOPER_TOKEN": settings.GOOGLE_ADS_DEVELOPER_TOKEN,
        "GOOGLE_ADS_CLIENT_ID":       settings.GOOGLE_ADS_CLIENT_ID,
        "GOOGLE_ADS_CLIENT_SECRET":   settings.GOOGLE_ADS_CLIENT_SECRET,
        "GOOGLE_ADS_REFRESH_TOKEN":   settings.GOOGLE_ADS_REFRESH_TOKEN,
        "GOOGLE_ADS_CUSTOMER_ID":     settings.GOOGLE_ADS_CUSTOMER_ID,
    }
 
    # Find any fields that are still empty strings
    missing = [key for key, value in required.items() if not value]
 
    if missing:
        raise RuntimeError(
            f"Missing Google Ads SDK credentials in .env: {', '.join(missing)}\n"
            f"Fill these in before starting the server."
        )
 
    print("Google Ads SDK credentials present.")

def handle_google_ads_error(ex: GoogleAdsException) -> str:
    """
    Turns a Google Ads API error into a readable string.
 
    When an SDK call fails (e.g. invalid campaign name, bad budget),
    Google throws a GoogleAdsException with technical error codes.
    This function formats that into plain English so the agent can
    log it and move on instead of crashing the whole pipeline.
 
    Example output:
    "[CAMPAIGN_ERROR] Campaign name already exists — field: name"
    """
    messages = []
    for error in ex.failure.errors:
        # Get the field name that caused the error, if Google tells us
        field = ""
        if error.location.field_path_elements:
            field = f" — field: {error.location.field_path_elements[-1].field_name}"
 
        messages.append(f"[{error.error_code}] {error.message}{field}")
 
    return " | ".join(messages)

