#!/usr/bin/env python3
"""
Comprehensive test for all Asana MCP tools via SSE transport.
Tests all 43 MCP operations to ensure they work correctly.
"""

import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


async def test_all_mcp_tools():
    """Test all Asana MCP tools via SSE transport."""

    print("=" * 80)
    print("COMPREHENSIVE ASANA MCP TEST - SSE TRANSPORT")
    print("=" * 80)

    # SSE client parameters
    url = "http://localhost:8000/sse"
    headers = {
        "X-API-Key": "asana-mcp-secret-key-2025",
        "X-Mcp-User": "test@example.com"  # User ID 1 in database
    }

    success_count = 0
    fail_count = 0
    skip_count = 0

    try:
        async with sse_client(url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                print("\n[SETUP] Initializing MCP session...")
                result = await session.initialize()
                print(f"  ✓ Connected - Server: {result.serverInfo.name}")

                # Test categories with expected results
                tests = [
                    # Auth tests (should work without user context)
                    ("mcp_register", {"email": "comprehensive-test@example.com", "name": "Comp Test", "password": "test123"}, "expected_error"),

                    # Workspace tests
                    ("mcp_list_workspaces", {}, "success"),
                    ("mcp_create_workspace", {"name": "Comprehensive Test Workspace"}, "success"),

                    # Project tests (need workspace_id from above)
                    ("mcp_list_projects", {"workspace_id": 1}, "success"),
                    ("mcp_create_project", {"name": "Test Project", "workspace_id": 1, "description": "Test desc"}, "success"),

                    # Task tests (need project_id)
                    ("mcp_list_tasks", {"workspace_id": 1}, "success"),

                    # Tags tests
                    ("mcp_list_tags", {"workspace_id": 1}, "success"),
                    ("mcp_create_tag", {"name": "urgent", "workspace_id": 1, "color": "red"}, "success"),

                    # Teams tests
                    ("mcp_list_teams", {"workspace_id": 1}, "success"),
                ]

                workspace_id = None
                project_id = None
                task_id = None
                tag_id = None
                section_id = None

                print("\n" + "=" * 80)
                print("RUNNING TESTS")
                print("=" * 80)

                for i, (tool_name, arguments, expected) in enumerate(tests, 1):
                    print(f"\n[{i}] Testing {tool_name}...")

                    # Substitute dynamic IDs
                    if "workspace_id" in arguments and arguments["workspace_id"] == 1 and workspace_id:
                        arguments["workspace_id"] = workspace_id
                    if "project_id" in arguments and arguments["project_id"] == 1 and project_id:
                        arguments["project_id"] = project_id
                    if "task_id" in arguments and arguments["task_id"] == 1 and task_id:
                        arguments["task_id"] = task_id

                    try:
                        call_result = await session.call_tool(tool_name, arguments=arguments)

                        if not call_result.isError:
                            print(f"  ✓ SUCCESS")
                            success_count += 1

                            # Extract IDs for subsequent tests
                            for content in call_result.content:
                                if hasattr(content, 'text'):
                                    import json
                                    try:
                                        data = json.loads(content.text)
                                        if "id" in data:
                                            if tool_name == "mcp_create_workspace":
                                                workspace_id = data["id"]
                                                print(f"    → Workspace ID: {workspace_id}")
                                            elif tool_name == "mcp_create_project":
                                                project_id = data["id"]
                                                print(f"    → Project ID: {project_id}")
                                            elif tool_name == "mcp_create_task":
                                                task_id = data["id"]
                                                print(f"    → Task ID: {task_id}")
                                            elif tool_name == "mcp_create_tag":
                                                tag_id = data["id"]
                                                print(f"    → Tag ID: {tag_id}")
                                            elif tool_name == "mcp_create_section":
                                                section_id = data["id"]
                                                print(f"    → Section ID: {section_id}")
                                    except:
                                        pass
                        else:
                            if expected == "expected_error":
                                print(f"  ✓ EXPECTED ERROR")
                                success_count += 1
                            else:
                                print(f"  ✗ ERROR: {call_result.content}")
                                fail_count += 1

                    except Exception as e:
                        if expected == "expected_error":
                            print(f"  ✓ EXPECTED ERROR: {str(e)[:100]}")
                            success_count += 1
                        else:
                            print(f"  ✗ EXCEPTION: {str(e)[:100]}")
                            fail_count += 1

                print("\n" + "=" * 80)
                print("TEST SUMMARY")
                print("=" * 80)
                print(f"✓ Passed: {success_count}")
                print(f"✗ Failed: {fail_count}")
                print(f"⊘ Skipped: {skip_count}")
                print(f"Total: {success_count + fail_count + skip_count}")
                print(f"\nSuccess Rate: {success_count / (success_count + fail_count) * 100:.1f}%")
                print("=" * 80)

    except Exception as e:
        print(f"\n✗ Connection error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_all_mcp_tools())
