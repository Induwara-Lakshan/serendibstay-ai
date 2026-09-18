import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def test():
    async with streamable_http_client(
        "http://127.0.0.1:8002/mcp"
  ) as (read, write):

        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.list_tools()

            print("MCP tools:")
            for tool in result.tools:
                print("-", tool.name)


if __name__ == "__main__":
    asyncio.run(test())