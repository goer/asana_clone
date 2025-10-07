#!/usr/bin/env python3
"""
Debug script for Asana MCP server using SSE transport.
Tests the MCP protocol with Server-Sent Events.
"""

import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


async def test_mcp_sse():
    """Test the Asana MCP server via SSE transport."""

    print("=" * 60)
    print("Asana MCP Server - SSE Transport Test")
    print("=" * 60)

    # SSE client parameters
    url = "http://localhost:8000/sse"
    headers = {
        "X-API-Key": "asana-mcp-secret-key-2025",
        "X-Mcp-User": "admin@example.com"
    }

    try:
        print("\n[1] Connecting to SSE endpoint...")
        async with sse_client(url, headers=headers) as (read, write):
            print("  ✓ Connected to SSE transport")

            async with ClientSession(read, write) as session:
                print("\n[2] Initializing MCP session...")
                result = await session.initialize()
                print(f"  ✓ Session initialized")
                print(f"  Server: {result.serverInfo.name}")
                print(f"  Protocol: {result.protocolVersion}")

                print("\n[3] Listing available tools...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"  ✓ Found {len(tools)} tools")

                if tools:
                    print("\n  Sample tools:")
                    for tool in tools[:10]:
                        desc = tool.description or "No description"
                        print(f"    - {tool.name}: {desc[:60]}...")

                    if len(tools) > 10:
                        print(f"    ... and {len(tools) - 10} more tools")

                # Test calling register tool
                print("\n[4] Testing tool call: mcp_register...")
                try:
                    register_result = await session.call_tool(
                        "mcp_register",
                        arguments={
                            "email": "ssetest@example.com",
                            "name": "SSE Test User",
                            "password": "ssepass123"
                        }
                    )

                    if not register_result.isError:
                        print("  ✓ User registered successfully!")
                        for content in register_result.content:
                            if hasattr(content, 'text'):
                                print(f"  Response: {content.text[:200]}")
                    else:
                        print(f"  ✗ Error: {register_result.content}")

                except Exception as e:
                    print(f"  ✗ Error calling tool: {e}")

                # Test calling list workspaces
                print("\n[5] Testing tool call: mcp_list_workspaces...")
                try:
                    list_ws_result = await session.call_tool(
                        "mcp_list_workspaces",
                        arguments={}
                    )

                    if not list_ws_result.isError:
                        print("  ✓ Workspaces listed successfully!")
                        for content in list_ws_result.content:
                            if hasattr(content, 'text'):
                                print(f"  Response: {content.text[:200]}")
                    else:
                        print(f"  ✗ Error: {list_ws_result.content}")

                except Exception as e:
                    print(f"  ✗ Error calling tool: {e}")

                # Test creating a workspace
                print("\n[6] Testing tool call: mcp_create_workspace...")
                try:
                    create_ws_result = await session.call_tool(
                        "mcp_create_workspace",
                        arguments={"name": "SSE Test Workspace"}
                    )

                    if not create_ws_result.isError:
                        print("  ✓ Workspace created successfully!")
                        for content in create_ws_result.content:
                            if hasattr(content, 'text'):
                                print(f"  Response: {content.text[:300]}")
                    else:
                        print(f"  ✗ Error: {create_ws_result.content}")

                except Exception as e:
                    print(f"  ✗ Error calling tool: {e}")

                print("\n" + "=" * 60)
                print("SSE Transport Test Complete!")
                print("=" * 60)

    except Exception as e:
        print(f"\n✗ Connection error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_sse())
