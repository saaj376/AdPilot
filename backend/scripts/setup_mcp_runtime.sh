#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MCP_RUNTIME_DIR="$BACKEND_DIR/.mcp-runtime"
MCP_PIP="$MCP_RUNTIME_DIR/bin/pip"
MCP_BIN="$MCP_RUNTIME_DIR/bin/google-ads-mcp"

if [[ ! -d "$MCP_RUNTIME_DIR" ]]; then
  python3 -m venv "$MCP_RUNTIME_DIR"
fi

"$MCP_PIP" install --upgrade pip
"$MCP_PIP" install --upgrade google-ads-mcp

echo "Isolated MCP runtime ready at: $MCP_RUNTIME_DIR"
echo "MCP command path: $MCP_BIN"
echo "Set GOOGLE_ADS_MCP_COMMAND to override if needed."
