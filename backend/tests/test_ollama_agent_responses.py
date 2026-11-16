import os
import pytest
from crewai import Crew, Process, Task
from agents.report_agent import report_agent
from services.llm_client import check_ollama_health

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_ollama_plan_summary():
    if os.getenv("RUN_OLLAMA_AGENT_TESTS") != "1":
        pytest.skip("Set RUN_OLLAMA_AGENT_TESTS=1 to run local model integration")
    await check_ollama_health()
    import asyncio
    agent = report_agent.copy()
    task = Task(description="Plan an A/B test for a vacuum with a washable filter. No ads have run.",
                expected_output="JSON with week_summary", agent=agent)
    output = await asyncio.to_thread(Crew(agents=[agent], tasks=[task], process=Process.sequential).kickoff)
    assert output.raw
