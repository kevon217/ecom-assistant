import json

import pytest
from agents.mcp.server import MCPServerSse

URL = "http://127.0.0.1:8002/mcp"


@pytest.mark.skip(
    reason="Requires running MCP server - integrate after core functionality works"
)
@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_tool_discovery_product():
    server = MCPServerSse(params={"url": URL}, cache_tools_list=True)
    await server.connect()
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert {
        "semantic_search",
        # "lexical_search",
        "get_metadata_options",
        "health",
    }.issubset(names)
    await server.cleanup()


async def _call(server, name, params):
    ev = await server.call_tool(name, params)
    text = ev.content[0].text
    payload = json.loads(text)
    return payload["result"]


@pytest.mark.skip(
    reason="Requires running MCP server - integrate after core functionality works"
)
@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_semantic_search_product():
    server = MCPServerSse(params={"url": URL}, cache_tools_list=True)
    await server.connect()
    result = await _call(
        server,
        "semantic_search",
        {"query": "wireless", "limit": 1, "metadata_filters": {}},
    )
    assert isinstance(result, list)
    await server.cleanup()
