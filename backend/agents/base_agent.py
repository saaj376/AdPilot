from pathlib import Path
from crewai import Agent
from services.llm_client import get_llm

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {path}\n"
            f"Make sure {filename} exists in the prompts/ folder."
        )
    return path.read_text(encoding="utf-8")


class BaseAgent:
    """
    Parent class for all 8 AdPilot agents.

    Holds the shared config that every agent needs:
      - llm          — Ollama gemma3:4b via CrewAI LLM
      - memory       — False (prevents CrewAI spinning up ChromaDB)
      - cache        — False (we don't want stale tool results between runs)
      - verbose      — True (logs agent thinking to console during dev)
      - max_iter     — 5 (stops infinite tool-calling loops)

    Each subclass calls build() with its own role, goal, backstory
    and tools to get a configured CrewAI Agent object.

    Usage in agent files:
        from app.agents.base_agent import BaseAgent

        research_agent = BaseAgent.build(
            role="Business Research Specialist",
            goal="Understand the business and its competitors",
            backstory="You are an expert at analysing businesses...",
            tools=[scrape_website, search_competitors],
        )
    """
    _llm = None

    @classmethod
    def _get_llm(cls):
        if cls._llm is None:
            cls._llm = get_llm()
        return cls._llm

    @classmethod
    def build(
        cls,
        role: str,
        goal: str,
        backstory: str,
        tools: list = None,
    ) -> Agent:
        """
        Creates and returns a configured CrewAI Agent.

        Args:
            role:      what this agent is e.g. "Google Ads Copywriter"
            goal:      what this agent is trying to achieve
            backstory: context that shapes how the agent thinks and responds
            tools:     list of @tool functions or MCPTool this agent can use
                       (pass an empty list or None for LLM-only agents)

        Returns:
            A fully configured CrewAI Agent ready to be added to the Crew.
        """
        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            tools=tools or [],
            llm=cls._get_llm(),

            # Never let CrewAI spin up ChromaDB for memory storage
            # We handle our own state via CampaignContext + Redis
            memory=False,

            # Always use fresh tool results — never cache between pipeline runs
            cache=False,

            # Print agent thinking to console — useful during development
            # Set to False in production if you want cleaner logs
            verbose=True,

            # Maximum number of tool calls before the agent gives up
            # Prevents infinite loops if a tool keeps returning unexpected results
            max_iter=5,
        )