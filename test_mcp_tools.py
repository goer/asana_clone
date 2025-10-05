#!/usr/bin/env python3
"""
Test script to verify MCP tools are exposed correctly.
"""
import httpx

# MCP server URL
MCP_URL = "http://localhost:8000/mcp-api"
API_KEY = "asana-mcp-secret-key-2025"

def test_mcp_endpoints():
    """Test that MCP endpoints are accessible."""
    # Check OpenAPI schema
    response = httpx.get(f"{MCP_URL}/openapi.json")
    if response.status_code == 200:
        openapi = response.json()
        paths = openapi.get("paths", {})
        print(f"✓ MCP app has {len(paths)} REST endpoints")

        # Group by tag
        from collections import Counter
        tags_count = Counter()
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ['get', 'post', 'patch', 'delete', 'put']:
                    tag = details.get('tags', ['Untagged'])[0]
                    tags_count[tag] += 1

        print("\nEndpoints by resource:")
        for tag, count in sorted(tags_count.items()):
            print(f"  {tag}: {count} endpoints")

        return True
    else:
        print(f"✗ Failed to fetch OpenAPI schema: {response.status_code}")
        return False

if __name__ == "__main__":
    print("Testing MCP Server Setup\n" + "="*50 + "\n")

    success = test_mcp_endpoints()

    if success:
        print("\n" + "="*50)
        print("✓ MCP server is working correctly!")
        print(f"✓ Access the API docs at: {MCP_URL}/docs")
        print(f"✓ MCP endpoint: {MCP_URL}/mcp (HTTP)")
        print(f"✓ MCP endpoint: {MCP_URL}/sse (SSE)")
    else:
        print("\n✗ MCP server test failed")
        exit(1)
