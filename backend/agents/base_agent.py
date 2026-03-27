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

    # Shared LLM instance — all agents use the same Ollama gemma3:4b
    _llm = None

    @staticmethod
    def _escape_braces_for_format(text: str) -> str:
        """Escape literal braces so CrewAI string interpolation does not treat JSON blocks as format fields."""
        return text.replace("{", "{{").replace("}", "}}")

    @classmethod
    def _get_llm(cls):
        # Create the LLM once and reuse it across all agents
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
        use_system_prompt: bool = True,
    ) -> Agent:
        """
        Creates and returns a configured CrewAI Agent.

        Args:
            role:               what this agent is e.g. "Google Ads Copywriter"
            goal:               what this agent is trying to achieve
            backstory:          context that shapes how the agent thinks and responds
            tools:              list of @tool functions or MCPTool this agent can use
                                (pass an empty list or None for LLM-only agents)
            use_system_prompt:  set False for tool-less agents so CrewAI does not
                                inject the ReAct Action/Observation scaffolding.
                                When a tool-less LLM goes straight to Final Answer,
                                CrewAI mistakenly rejects it as a format error and
                                retries until max_iter is exhausted.

        Returns:
            A fully configured CrewAI Agent ready to be added to the Crew.
        """
        safe_backstory = cls._escape_braces_for_format(backstory)

        # Bug 6 fix: If agent has tools, it MUST follow the ReAct format (Action/Observation/Final Answer).
        # We inject a strict instruction to prevent the "Action required after Thought" parse errors.
        if use_system_prompt and tools:
            safe_backstory += (
                "\n\nCRITICAL INSTRUCTION ON FORMAT:\n"
                "You must always follow the ReAct pattern:\n"
                "1. Thought: <your thinking>\n"
                "2. Action: <the tool to call> (must be one of: " + (", ".join([t.name for t in tools])) + ")\n"
                "3. Action Input: <the JSON input to the tool>\n\n"
                "If you do not need to use any tools to answer the prompt, skip the Action "
                "and go straight to your Final Answer using this EXACT format:\n"
                "Thought: I have sufficient information to answer.\n"
                "Final Answer: <your complete answer here>\n\n"
                "Failure to use this exact format will cause a system error."
            )

        return Agent(
            role=role,
            goal=goal,
            backstory=safe_backstory,
            tools=tools or [],
            llm=cls._get_llm(),

            # Whether to inject the ReAct (Thought/Action/Observation) system prompt.
            # Tool-using agents need it; pure-LLM agents should set this to False
            # so the LLM can write Final Answer directly without format errors.
            use_system_prompt=use_system_prompt,

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
            max_iter=8,

            # Maximum number of parse-error retries before CrewAI forces a final answer.
            # Default is unlimited — 2 retries is enough for a local LLM.
            max_retry_limit=2,
        )