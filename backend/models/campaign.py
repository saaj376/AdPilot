from enum import Enum
from pydantic import BaseModel, Field

#this is a google ads concept, when we add a keyword to a campaign, we can specify how closely the keyword should match the user's search query.
#the keyword agent would be using this to build realistic keywords for the campaign, and the ad agent would be using this to build realistic ads for the campaign.
class MatchType(str, Enum):
    BROAD   = "BROAD"
    PHRASE  = "PHRASE"
    EXACT   = "EXACT"
 
#this one shows the current status of the campaign, the campaign agent would be using this to update the status of the campaign as it progresses through the pipeline, and the ad agent would be using this to determine which ads to create based on the current status of the campaign.
class CampaignStatus(str, Enum):
    PENDING  = "PENDING"
    RUNNING  = "RUNNING"
    LAUNCHED = "LAUNCHED"
    PAUSED   = "PAUSED"
    DONE     = "DONE"
    FAILED   = "FAILED"

#one keyword in a campaign will contain 4 fields. The text field is the actual keyword text, the match_type field is how broadly google matches it, defaults to BROAD.
#the bid field is CPC-Cost per click, which is how much the advertiser is willing to pay for each click on an ad triggered by this keyword, defaults to 1.0. 
#the quality_score field is google's score from 1 to 10 for how relevant the keyword is to the ads and landing page, which can affect the ad's performance and cost, defaults to None since it will be determined by google after the campaign is launched.
class Keyword(BaseModel):
    text:           str
    match_type:     MatchType   = MatchType.BROAD
    bid:            float       = 1.0       
    quality_score:  int | None  = None  

#one responsive search ad. the constraints are min length=3, max length=15 for headlines, and min length=2, max length=4 for descriptions.
#this actually matches to the google ads' actual limit for responsive search ads. we're only mocking, but we're planning to match industry traditional practises.
#the creative agent prompt can say "write between 3 and 15 headlines" and it maps directly to the model
#the mock data looks legitimate to a google reviewer. 
class Ad(BaseModel):
    headlines:      list[str]   = Field(min_length=3,  max_length=15)  
    descriptions:   list[str]   = Field(min_length=2,  max_length=4)   
    final_url:      str         = "https://example.com"


#this is a container which sits in between campaign and its keywords/ads. In Google Ads, you group related keywords together so they share the same ads.
#the launch agent creates these groupings based on what the keyword agent and creative agent produced. 
class AdGroup(BaseModel):
    name:       str
    keywords:   list[Keyword]   = []
    ads:        list[Ad]        = []

#this has monthly budget and daily budget. Google ADS works on daily budgets.
#the launch agent converts daily budget to monly budget by multiplying by 30.4, which is the average number of days in a month.
#Keeping both in the model means the frontend can show the user their monthly spend while the mock tools use the daily figure.
#geo_targets is a list of strings like ["Austin, TX", "San Antonio, TX"]. The LaunchAgent passes these to the mock create_campaign tool.
class Campaign(BaseModel):
    id:             str
    name:           str
    status:         CampaignStatus  = CampaignStatus.PENDING
    monthly_budget: float           = 0.0
    daily_budget:   float           = 0.0
    geo_targets:    list[str]       = []
    ad_groups:      list[AdGroup]   = []

#this is what the frontend will send to POST/campaigns. the three things are field of min length 20 on business description which forces the user to write something meaningful. the research agent needs this to work with.
#the budget should be greater than 0, and the geo targets default to United States if the user doesn't specify any. The launch agent will use this information to create the campaign and pass it to the mock tools.
class CampaignCreateRequest(BaseModel):
    business_description:   str             = Field(min_length=20)
    monthly_budget:         float           = Field(gt=0)
    geo_targets:            list[str]       = ["United States"]


class CampaignCreateResponse(BaseModel):
    campaign_id:    str
    status:         CampaignStatus  = CampaignStatus.PENDING
    message:        str             = "Pipeline started. Connect to /live/{campaign_id} for live updates."