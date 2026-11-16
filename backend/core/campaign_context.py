#campaign_context.py is a shared notebook passed between all the 8 agents. 
#Each agent reads what previous agents wrote, does its job, and writes its own output into it.

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from models.campaign import Campaign, CampaignStatus
from models.agent_run import AgentRunState, AgentStatus


#it is a simple class of string constants representing the names of the agents in the campaign workflow.
class AgentName:
    RESEARCH  = "ResearchAgent"
    KEYWORD   = "KeywordAgent"
    CREATIVE  = "CreativeAgent"
    QA        = "QAAgent"
    LAUNCH    = "LaunchAgent"
    MONITOR   = "MonitorAgent"
    OPTIMIZE  = "OptimizeAgent"
    REPORT    = "ReportAgent"
 
    ALL = [RESEARCH, KEYWORD, CREATIVE, QA, LAUNCH, MONITOR, OPTIMIZE, REPORT]


#
class CampaignContext(BaseModel):

#these are the inputs which will be provided by the user when they hit POST/campaigns. 
    research_brief: dict | None = None
    landing_page_url:       str = ""
    campaign_id:            str
    business_description:   str
    monthly_budget:         float
    geo_targets:            list[str]       = ["United States"]
    created_at:             datetime        = Field(default_factory=lambda: datetime.now(timezone.utc))

    campaign_status:        CampaignStatus  = CampaignStatus.PENDING
 
    # ── Agent outputs — filled in one by one as each agent completes ──────────
    business_profile:       dict            = {}    # ResearchAgent
    keyword_strategy:       dict            = {}    # KeywordAgent
    ad_creatives:           dict            = {}    # CreativeAgent
    qa_result:              dict            = {}    # QAAgent
    campaign_ids:           dict            = {}    # LaunchAgent
    performance_data:       dict            = {}    # MonitorAgent
    optimizations:          dict            = {}    # OptimizeAgent
    weekly_report:          str             = ""    # ReportAgent
 
    agent_states:           dict[str, AgentRunState] = {}

    campaign:               Campaign | None  = None
 
#it is a special method that runs automatically right after __init__ completes. 
#The check says "only initialise if it's empty, i.e. this is a brand new context."
    def model_post_init(self, __context):
        """Initialise all 8 agent states to IDLE on creation."""
        if not self.agent_states:
            self.agent_states = {
                name: AgentRunState(agent_name=name)
                for name in AgentName.ALL
            }
 
#These are called by crew.py's on_step() callback. You never call them directly from agent files — only from the orchestration layer.
    def set_agent_running(self, agent_name: str):
        self.agent_states[agent_name].status     = AgentStatus.RUNNING
        self.agent_states[agent_name].started_at = datetime.now(timezone.utc)
        self.campaign_status                      = CampaignStatus.RUNNING
 
    def set_agent_done(self, agent_name: str, output: dict | None = None):
        state              = self.agent_states[agent_name]
        state.status       = AgentStatus.DONE
        state.output       = output
        state.finished_at  = datetime.now(timezone.utc)
 
    def set_agent_failed(self, agent_name: str, error: str):
        state              = self.agent_states[agent_name]
        state.status       = AgentStatus.FAILED
        state.finished_at  = datetime.now(timezone.utc)
        self.campaign_status = CampaignStatus.FAILED
 
    def add_log(self, agent_name: str, message: str, level: str = "INFO"):
        from models.agent_run import AgentLog, LogLevel

        if agent_name not in self.agent_states:
            # Allow system-level channels (for example "pipeline") without crashing.
            self.agent_states[agent_name] = AgentRunState(agent_name=agent_name)

        log = AgentLog(
            agent_name=agent_name,
            message=message,
            level=LogLevel(level),
        )
        self.agent_states[agent_name].logs.append(log)
        return log
 
    def is_complete(self) -> bool:
        return all(
            s.status == AgentStatus.DONE
            for s in self.agent_states.values()
        )
 
    def duration_seconds(self, agent_name: str) -> float | None:
        state = self.agent_states[agent_name]
        if state.started_at and state.finished_at:
            return (state.finished_at - state.started_at).total_seconds()
        return None
 