from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

#this tells us the four states any agent can be in at any given time in the pipeline. 
class AgentStatus(str, Enum):
    IDLE    = "IDLE"
    RUNNING = "RUNNING"
    DONE    = "DONE"
    FAILED  = "FAILED"

#this has three levels of logs that an agent can emit during its run. info for normal progress, warn for potential or soft issues for example like a keyword was skipped because CPC was too high and error for things that went wrong but didn't kill the agent. 
class LogLevel(str, Enum):
    INFO  = "INFO"
    WARN  = "WARN"
    ERROR = "ERROR"

# this is the structure of a log message emitted by an agent during its run. it includes the agent name, the log message, the log level and a timestamp.
#means every log line automatically gets the current UTC time without you having to pass it manually.
# This is what the WebSocket streams to the frontend in real time — each time an agent emits a log, a new AgentLog is created and pushed.
class AgentLog(BaseModel):
    agent_name: str
    message:    str
    level:      LogLevel            = LogLevel.INFO
    timestamp:  datetime            = Field(default_factory=lambda: datetime.now(timezone.utc))


#agent run state gives the complete picture of one agent across it's entire run. 
#logs accumulates every AgentLog the agent emits. output is the final result dict the agent produced — None until it finishes. started_at and finished_at let you calculate how long each agent took, which you can show in the frontend
class AgentRunState(BaseModel):
    agent_name: str
    status:     AgentStatus         = AgentStatus.IDLE
    logs:       list[AgentLog]      = []
    output:     dict | None         = None
    started_at: datetime | None     = None
    finished_at: datetime | None    = None

#this is the thing that actually travels over the WebSocket. 
#Every time an agent changes state or emits a log, crew.py's on_step() callback creates a PipelineEvent and publishes it to the event_bus
# The WebSocket endpoint serialises it to JSON and sends it to the frontend. It bundles everything the frontend needs in one packet — which campaign, which agent, what status, and optionally the latest log line.
class PipelineEvent(BaseModel):
    campaign_id: str
    agent_name:  str
    status:      AgentStatus
    output:      dict | None       = None
    log:         AgentLog | None    = None
    timestamp:   datetime           = Field(default_factory=lambda: datetime.now(timezone.utc))