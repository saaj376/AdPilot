import json
import os
import shutil
from pathlib import Path
from typing import Any

import anyio
from crewai.tools import tool
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from config import settings


# The official Google Ads MCP server is now installed directly
# in your .venv via: pip install git+https://github.com/googleads/google-ads-mcp.git
#
# Because it's installed as a package (not run via pipx),
# we launch it using the installed command "google-ads-mcp"
# directly — no pipx needed.
#
# This tool is READ-ONLY — it can only fetch data, never change anything.
# That's exactly what MonitorAgent needs: read campaign performance via GAQL.
#
# Two tools exposed to the agent:
#   1. list_accessible_customers — lists all Google Ads accounts you can access
#   2. search — runs a GAQL query and returns performance data
#
# MonitorAgent uses "search" to ask things like:
# "Give me CTR, CPC, impressions and spend for campaign X this week"
# and gets back real data from the Google Ads API.


def _resolve_mcp_command() -> str | None:
    """Resolve the MCP command, preferring the isolated Option-B runtime."""
    env_command = os.getenv("GOOGLE_ADS_MCP_COMMAND", "").strip()
    if env_command:
        return env_command

    backend_dir = Path(__file__).resolve().parents[1]
    isolated_cmd = backend_dir / ".mcp-runtime" / "bin" / "google-ads-mcp"
    if isolated_cmd.is_file():
        return str(isolated_cmd)

    path_cmd = shutil.which("google-ads-mcp")
    if path_cmd:
        return path_cmd

    return None


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _build_server_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update({k: v for k, v in settings.google_ads_mcp_env.items() if v})
    return env


def _validate_adc_credentials() -> None:
    """Validate ADC file shape early so MCP failures are actionable."""
    cred_path = settings.GOOGLE_APPLICATION_CREDENTIALS
    if not cred_path:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS is empty.")

    path = Path(cred_path)
    if not path.is_file():
        raise RuntimeError(
            f"GOOGLE_APPLICATION_CREDENTIALS does not exist: {cred_path}"
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"GOOGLE_APPLICATION_CREDENTIALS is not valid JSON: {exc}"
        ) from exc

    allowed_types = {
        "authorized_user",
        "service_account",
        "external_account",
        "external_account_authorized_user",
        "impersonated_service_account",
        "gdch_service_account",
    }
    cred_type = payload.get("type")
    if cred_type not in allowed_types:
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS must be ADC JSON with a valid `type` "
            "(authorized_user/service_account/etc), not an OAuth client_secret file."
        )


def _serialize_result(result: Any) -> str:
    """Normalize MCP call result to a JSON string for CrewAI consumption."""
    content = getattr(result, "content", None)
    if isinstance(content, list) and content:
        if len(content) == 1 and hasattr(content[0], "text"):
            return str(content[0].text)
        normalized = []
        for item in content:
            if hasattr(item, "text"):
                normalized.append(item.text)
            elif hasattr(item, "model_dump"):
                normalized.append(item.model_dump())
            else:
                normalized.append(str(item))
        return json.dumps(normalized, ensure_ascii=True)

    if hasattr(result, "model_dump"):
        return json.dumps(result.model_dump(), ensure_ascii=True)
    return str(result)


def _flatten_exception(exc: BaseException) -> str:
    if isinstance(exc, ExceptionGroup) and exc.exceptions:
        return _flatten_exception(exc.exceptions[0])
    return f"{type(exc).__name__}: {exc}"


async def _call_mcp_tool_async(tool_name: str, arguments: dict[str, Any]) -> str:
    if not MCP_COMMAND:
        raise RuntimeError(
            "google-ads-mcp command is unavailable. "
            "Run backend/scripts/setup_mcp_runtime.sh or set GOOGLE_ADS_MCP_COMMAND."
        )

    server = StdioServerParameters(
        command=MCP_COMMAND,
        args=[],
        env=_build_server_env(),
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return _serialize_result(result)


def _call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    _validate_adc_credentials()
    return anyio.run(_call_mcp_tool_async, tool_name, arguments)


@tool("google_ads_mcp_list_accessible_customers")
def mcp_list_accessible_customers() -> str:
    """List customer IDs available to the configured Google Ads account."""
    try:
        return _call_mcp_tool("list_accessible_customers", {})
    except Exception as exc:
        return f"MCP list_accessible_customers failed: {_flatten_exception(exc)}"


@tool("google_ads_mcp_search")
def mcp_reader(
    customer_id: str,
    fields_csv: str,
    resource: str,
    conditions_csv: str = "",
    orderings_csv: str = "",
    limit: int = 100,
) -> str:
    """Run the Google Ads MCP `search` tool with structured query parts.

    Args:
        customer_id: Google Ads customer id digits only (example: 1234567890).
        fields_csv: Comma-separated fields (example: campaign.id,metrics.clicks).
        resource: GAQL resource name (example: campaign or keyword_view).
        conditions_csv: Optional comma-separated filters.
        orderings_csv: Optional comma-separated order clauses.
        limit: Maximum rows to return.
    """
    payload: dict[str, Any] = {
        "customer_id": customer_id,
        "fields": _split_csv(fields_csv),
        "resource": resource,
        "conditions": _split_csv(conditions_csv),
        "orderings": _split_csv(orderings_csv),
        "limit": int(limit),
    }
    try:
        return _call_mcp_tool("search", payload)
    except Exception as exc:
        return f"MCP search failed: {_flatten_exception(exc)}"


MCP_COMMAND = _resolve_mcp_command()