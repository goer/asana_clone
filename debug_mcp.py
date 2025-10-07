#!/usr/bin/env python3
"""
Debug script for Asana MCP server.
Tests the MCP protocol flow and authentication.
"""

import asyncio
import json
import httpx


async def debug_mcp_server():
    """Test the Asana MCP server with proper protocol flow."""

    base_url = "http://localhost:8000/mcp"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "X-API-Key": "asana-mcp-secret-key-2025",
        "X-Mcp-User": "admin@example.com"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 60)
        print("Asana MCP Server Debug Script")
        print("=" * 60)

        # Test 1: Initialize MCP session
        print("\n[1] Testing MCP Initialize...")
        try:
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "debug-script",
                        "version": "1.0.0"
                    }
                }
            }

            init_resp = await client.post(base_url, headers=headers, json=init_payload)
            print(f"  Status: {init_resp.status_code}")
            print(f"  Headers: {dict(init_resp.headers)}")

            init_result = init_resp.json()
            print(f"  Response: {json.dumps(init_result, indent=2)}")

            # Get session ID
            session_id = init_resp.headers.get("mcp-session-id")
            if session_id:
                print(f"  ✓ Session ID: {session_id}")
                headers["Mcp-Session-Id"] = session_id
            else:
                print("  ✗ No session ID in response!")
                return

        except Exception as e:
            print(f"  ✗ Error: {e}")
            return

        # Test 2: List Tools
        print("\n[2] Testing tools/list...")
        try:
            tools_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            tools_resp = await client.post(base_url, headers=headers, json=tools_payload)
            print(f"  Status: {tools_resp.status_code}")

            tools_result = tools_resp.json()
            if "error" in tools_result:
                print(f"  ✗ Error: {tools_result['error']}")
            elif "result" in tools_result:
                tools = tools_result["result"].get("tools", [])
                print(f"  ✓ Found {len(tools)} tools")
                if tools:
                    print("  Tools:")
                    for tool in tools[:5]:  # Show first 5
                        print(f"    - {tool.get('name')}: {tool.get('description', 'No description')[:60]}")
                    if len(tools) > 5:
                        print(f"    ... and {len(tools) - 5} more")
            else:
                print(f"  Response: {json.dumps(tools_result, indent=2)}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

        # Test 3: Call a tool (register user)
        print("\n[3] Testing tools/call (mcp_register)...")
        try:
            call_payload = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "mcp_register",
                    "arguments": {
                        "email": "debug@example.com",
                        "name": "Debug User",
                        "password": "debugpass123"
                    }
                }
            }

            call_resp = await client.post(base_url, headers=headers, json=call_payload)
            print(f"  Status: {call_resp.status_code}")

            call_result = call_resp.json()
            if "error" in call_result:
                print(f"  ✗ Error: {call_result['error']}")
            elif "result" in call_result:
                print(f"  ✓ Success!")
                print(f"  Response: {json.dumps(call_result['result'], indent=2)}")
            else:
                print(f"  Response: {json.dumps(call_result, indent=2)}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

        # Test 4: List workspaces
        print("\n[4] Testing tools/call (mcp_list_workspaces)...")
        try:
            list_ws_payload = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "mcp_list_workspaces",
                    "arguments": {}
                }
            }

            list_ws_resp = await client.post(base_url, headers=headers, json=list_ws_payload)
            print(f"  Status: {list_ws_resp.status_code}")

            list_ws_result = list_ws_resp.json()
            if "error" in list_ws_result:
                print(f"  ✗ Error: {list_ws_result['error']}")
            elif "result" in list_ws_result:
                print(f"  ✓ Success!")
                print(f"  Response: {json.dumps(list_ws_result['result'], indent=2)}")
            else:
                print(f"  Response: {json.dumps(list_ws_result, indent=2)}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

        # Test 5: Create workspace
        print("\n[5] Testing tools/call (mcp_create_workspace)...")
        try:
            create_ws_payload = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "mcp_create_workspace",
                    "arguments": {
                        "name": "Debug Test Workspace"
                    }
                }
            }

            create_ws_resp = await client.post(base_url, headers=headers, json=create_ws_payload)
            print(f"  Status: {create_ws_resp.status_code}")

            create_ws_result = create_ws_resp.json()
            if "error" in create_ws_result:
                print(f"  ✗ Error: {create_ws_result['error']}")
            elif "result" in create_ws_result:
                print(f"  ✓ Success!")
                print(f"  Response: {json.dumps(create_ws_result['result'], indent=2)}")
            else:
                print(f"  Response: {json.dumps(create_ws_result, indent=2)}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

        print("\n" + "=" * 60)
        print("Debug session complete!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(debug_mcp_server())
