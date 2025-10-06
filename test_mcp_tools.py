#!/usr/bin/env python3
"""
Comprehensive MCP Tools Testing Script

Tests all 43 MCP operations exposed by the Asana Clone MCP server.
"""
import os
import json
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("MCP_API_KEY", "asana-mcp-secret-key-2025")

# Test results storage
test_results = {
    "timestamp": datetime.now().isoformat(),
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "categories": {},
    "details": []
}

# Test data storage
test_data = {
    "token": None,
    "user_id": None,
    "workspace_id": None,
    "project_id": None,
    "task_id": None,
    "section_id": None,
    "comment_id": None,
    "tag_id": None,
    "team_id": None,
    "attachment_id": None,
    "custom_field_id": None,
}


def log_test(category, name, method, endpoint, status, details=""):
    """Log a test result."""
    test_results["total_tests"] += 1

    if status == "PASS":
        test_results["passed"] += 1
        icon = "✅"
    elif status == "FAIL":
        test_results["failed"] += 1
        icon = "❌"
    else:  # SKIP
        test_results["skipped"] += 1
        icon = "⏭️"

    if category not in test_results["categories"]:
        test_results["categories"][category] = {"passed": 0, "failed": 0, "skipped": 0}

    test_results["categories"][category][status.lower() if status.lower() in ["passed", "failed", "skipped"] else "failed"] += 1

    result = {
        "category": category,
        "name": name,
        "method": method,
        "endpoint": endpoint,
        "status": status,
        "details": details
    }
    test_results["details"].append(result)

    print(f"{icon} {category:20} {method:6} {endpoint:50} - {status}")
    if details and status == "FAIL":
        print(f"   └─ {details}")


def test_mcp_endpoint(category, name, method, path, data=None, headers=None, expected_status=200):
    """Test an MCP endpoint."""
    url = f"{BASE_URL}{path}"

    # Add API key to headers
    if headers is None:
        headers = {}
    headers["X-API-Key"] = API_KEY

    # Add auth token if available and not auth endpoint
    if test_data["token"] and "/auth/" not in path:
        headers["Authorization"] = f"Bearer {test_data['token']}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PATCH":
            response = requests.patch(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            log_test(category, name, method, path, "SKIP", f"Unsupported method: {method}")
            return None

        if response.status_code == expected_status:
            log_test(category, name, method, path, "PASS", f"Status {response.status_code}")
            return response.json() if response.content and expected_status != 204 else {}
        else:
            log_test(category, name, method, path, "FAIL",
                    f"Expected {expected_status}, got {response.status_code}: {response.text[:100]}")
            return None

    except Exception as e:
        log_test(category, name, method, path, "FAIL", f"Exception: {str(e)[:100]}")
        return None


print("=" * 80)
print(" MCP TOOLS COMPREHENSIVE TEST")
print("=" * 80)
print(f"Base URL: {BASE_URL}")
print(f"API Key: {API_KEY[:10]}...")
print("=" * 80)
print()

# AUTHENTICATION TESTS
print("\n📋 AUTHENTICATION")
print("-" * 80)

result = test_mcp_endpoint(
    "Authentication", "Register User", "POST", "/auth/register",
    data={"email": "mcp_test3@example.com", "name": "MCP Test User", "password": "testpass123"},
    expected_status=201
)
if result:
    test_data["token"] = result.get("token")
    test_data["user_id"] = result.get("user", {}).get("id") or result.get("user_id")

test_mcp_endpoint(
    "Authentication", "Login User", "POST", "/auth/login",
    data={"email": "mcp_test3@example.com", "password": "testpass123"},
    expected_status=200
)

# WORKSPACE TESTS
print("\n📋 WORKSPACES")
print("-" * 80)

result = test_mcp_endpoint(
    "Workspaces", "Create Workspace", "POST", "/workspaces",
    data={"name": "MCP Test Workspace"},
    expected_status=201
)
if result:
    test_data["workspace_id"] = result.get("id")

test_mcp_endpoint(
    "Workspaces", "List Workspaces", "GET", "/workspaces",
    expected_status=200
)

if test_data["workspace_id"]:
    test_mcp_endpoint(
        "Workspaces", "Get Workspace", "GET", f"/workspaces/{test_data['workspace_id']}",
        expected_status=200
    )
    test_mcp_endpoint(
        "Workspaces", "Update Workspace", "PATCH", f"/workspaces/{test_data['workspace_id']}",
        data={"name": "MCP Test Workspace Updated"},
        expected_status=200
    )

# PROJECT TESTS
print("\n📋 PROJECTS")
print("-" * 80)

if test_data["workspace_id"]:
    result = test_mcp_endpoint(
        "Projects", "Create Project", "POST", "/projects",
        data={
            "name": "MCP Test Project",
            "description": "Testing MCP tools",
            "workspace_id": test_data["workspace_id"],
            "is_public": True
        },
        expected_status=201
    )
    if result:
        test_data["project_id"] = result.get("id")

    test_mcp_endpoint(
        "Projects", "List Projects", "GET", f"/projects?workspace_id={test_data['workspace_id']}",
        expected_status=200
    )

if test_data["project_id"]:
    test_mcp_endpoint(
        "Projects", "Get Project", "GET", f"/projects/{test_data['project_id']}",
        expected_status=200
    )
    test_mcp_endpoint(
        "Projects", "Update Project", "PATCH", f"/projects/{test_data['project_id']}",
        data={"name": "MCP Test Project Updated"},
        expected_status=200
    )

# SECTION TESTS
print("\n📋 SECTIONS")
print("-" * 80)

if test_data["project_id"]:
    result = test_mcp_endpoint(
        "Sections", "Create Section", "POST", "/sections",
        data={"name": "To Do", "project_id": test_data["project_id"]},
        expected_status=201
    )
    if result:
        test_data["section_id"] = result.get("id")

    test_mcp_endpoint(
        "Sections", "List Sections", "GET", f"/sections?project_id={test_data['project_id']}",
        expected_status=200
    )

if test_data["section_id"]:
    test_mcp_endpoint(
        "Sections", "Update Section", "PATCH", f"/sections/{test_data['section_id']}",
        data={"name": "In Progress"},
        expected_status=200
    )

# TASK TESTS
print("\n📋 TASKS")
print("-" * 80)

if test_data["project_id"]:
    result = test_mcp_endpoint(
        "Tasks", "Create Task", "POST", "/tasks",
        data={
            "name": "MCP Test Task",
            "project_id": test_data["project_id"],
            "description": "Testing task creation via MCP",
            "section_id": test_data.get("section_id"),
            "completed": False
        },
        expected_status=201
    )
    if result:
        test_data["task_id"] = result.get("id")

if test_data["workspace_id"]:
    test_mcp_endpoint(
        "Tasks", "List Tasks", "GET", f"/tasks?workspace_id={test_data['workspace_id']}",
        expected_status=200
    )

if test_data["task_id"]:
    test_mcp_endpoint(
        "Tasks", "Get Task", "GET", f"/tasks/{test_data['task_id']}",
        expected_status=200
    )
    test_mcp_endpoint(
        "Tasks", "Update Task", "PATCH", f"/tasks/{test_data['task_id']}",
        data={"name": "MCP Test Task Updated", "completed": True},
        expected_status=200
    )

# COMMENT TESTS
print("\n📋 COMMENTS")
print("-" * 80)

if test_data["task_id"]:
    result = test_mcp_endpoint(
        "Comments", "Create Comment", "POST", f"/tasks/{test_data['task_id']}/comments",
        data={"content": "This is a test comment from MCP"},
        expected_status=201
    )
    if result:
        test_data["comment_id"] = result.get("id")

    test_mcp_endpoint(
        "Comments", "List Comments", "GET", f"/tasks/{test_data['task_id']}/comments",
        expected_status=200
    )

if test_data["comment_id"]:
    test_mcp_endpoint(
        "Comments", "Update Comment", "PATCH", f"/comments/{test_data['comment_id']}",
        data={"content": "Updated comment via MCP"},
        expected_status=200
    )

# TAG TESTS
print("\n📋 TAGS")
print("-" * 80)

if test_data["workspace_id"]:
    result = test_mcp_endpoint(
        "Tags", "Create Tag", "POST", "/tags",
        data={"name": "mcp-test", "workspace_id": test_data["workspace_id"], "color": "#FF5733"},
        expected_status=201
    )
    if result:
        test_data["tag_id"] = result.get("id")

    test_mcp_endpoint(
        "Tags", "List Tags", "GET", f"/tags?workspace_id={test_data['workspace_id']}",
        expected_status=200
    )

if test_data["tag_id"]:
    test_mcp_endpoint(
        "Tags", "Update Tag", "PATCH", f"/tags/{test_data['tag_id']}",
        data={"name": "mcp-test-updated", "color": "#33FF57"},
        expected_status=200
    )

if test_data["task_id"] and test_data["tag_id"]:
    test_mcp_endpoint(
        "Tags", "Add Tag to Task", "POST", f"/tags/tasks/{test_data['task_id']}/tags/{test_data['tag_id']}",
        expected_status=204
    )
    test_mcp_endpoint(
        "Tags", "Remove Tag from Task", "DELETE", f"/tags/tasks/{test_data['task_id']}/tags/{test_data['tag_id']}",
        expected_status=204
    )

# TEAM TESTS
print("\n📋 TEAMS")
print("-" * 80)

if test_data["workspace_id"]:
    result = test_mcp_endpoint(
        "Teams", "Create Team", "POST", "/teams",
        data={"name": "MCP Test Team", "workspace_id": test_data["workspace_id"], "description": "Testing teams"},
        expected_status=201
    )
    if result:
        test_data["team_id"] = result.get("id")

    test_mcp_endpoint(
        "Teams", "List Teams", "GET", f"/teams?workspace_id={test_data['workspace_id']}",
        expected_status=200
    )

if test_data["team_id"] and test_data["user_id"]:
    test_mcp_endpoint(
        "Teams", "Add Team Member", "POST", f"/teams/{test_data['team_id']}/members?user_id={test_data['user_id']}",
        expected_status=204
    )
    test_mcp_endpoint(
        "Teams", "Remove Team Member", "DELETE", f"/teams/{test_data['team_id']}/members/{test_data['user_id']}",
        expected_status=204
    )

# ATTACHMENT TESTS
print("\n📋 ATTACHMENTS")
print("-" * 80)

if test_data["task_id"]:
    result = test_mcp_endpoint(
        "Attachments", "Create Attachment", "POST", f"/tasks/{test_data['task_id']}/attachments",
        data={"filename": "test.pdf", "file_url": "https://example.com/test.pdf", "file_size": 1024},
        expected_status=201
    )
    if result:
        test_data["attachment_id"] = result.get("id")

    test_mcp_endpoint(
        "Attachments", "List Attachments", "GET", f"/tasks/{test_data['task_id']}/attachments",
        expected_status=200
    )

# CUSTOM FIELD TESTS
print("\n📋 CUSTOM FIELDS")
print("-" * 80)

if test_data["project_id"]:
    result = test_mcp_endpoint(
        "Custom Fields", "Create Custom Field", "POST", f"/projects/{test_data['project_id']}/custom-fields",
        data={"name": "Priority", "field_type": "select", "options": ["Low", "Medium", "High"]},
        expected_status=201
    )
    if result:
        test_data["custom_field_id"] = result.get("id")

    test_mcp_endpoint(
        "Custom Fields", "List Custom Fields", "GET", f"/projects/{test_data['project_id']}/custom-fields",
        expected_status=200
    )

if test_data["task_id"] and test_data["custom_field_id"]:
    test_mcp_endpoint(
        "Custom Fields", "Set Custom Field Value", "POST",
        f"/tasks/{test_data['task_id']}/custom-fields/{test_data['custom_field_id']}",
        data={"value": "High"},
        expected_status=204
    )
    test_mcp_endpoint(
        "Custom Fields", "Clear Custom Field Value", "DELETE",
        f"/tasks/{test_data['task_id']}/custom-fields/{test_data['custom_field_id']}",
        expected_status=204
    )

# CLEANUP
print("\n📋 CLEANUP / DELETE OPERATIONS")
print("-" * 80)

if test_data["comment_id"]:
    test_mcp_endpoint("Comments", "Delete Comment", "DELETE", f"/comments/{test_data['comment_id']}", expected_status=204)

if test_data["attachment_id"]:
    test_mcp_endpoint("Attachments", "Delete Attachment", "DELETE", f"/attachments/{test_data['attachment_id']}", expected_status=204)

if test_data["custom_field_id"]:
    test_mcp_endpoint("Custom Fields", "Delete Custom Field", "DELETE", f"/custom-fields/{test_data['custom_field_id']}", expected_status=204)

if test_data["tag_id"]:
    test_mcp_endpoint("Tags", "Delete Tag", "DELETE", f"/tags/{test_data['tag_id']}", expected_status=204)

if test_data["section_id"]:
    test_mcp_endpoint("Sections", "Delete Section", "DELETE", f"/sections/{test_data['section_id']}", expected_status=204)

if test_data["task_id"]:
    test_mcp_endpoint("Tasks", "Delete Task", "DELETE", f"/tasks/{test_data['task_id']}", expected_status=204)

if test_data["project_id"]:
    test_mcp_endpoint("Projects", "Delete Project", "DELETE", f"/projects/{test_data['project_id']}", expected_status=204)

if test_data["workspace_id"]:
    test_mcp_endpoint("Workspaces", "Delete Workspace", "DELETE", f"/workspaces/{test_data['workspace_id']}", expected_status=204)

# SUMMARY
print("\n" + "=" * 80)
print(" TEST SUMMARY")
print("=" * 80)
print(f"Total Tests:  {test_results['total_tests']}")
print(f"✅ Passed:    {test_results['passed']} ({test_results['passed']/test_results['total_tests']*100:.1f}%)")
print(f"❌ Failed:    {test_results['failed']} ({test_results['failed']/test_results['total_tests']*100:.1f}%)")
print(f"⏭️  Skipped:   {test_results['skipped']} ({test_results['skipped']/test_results['total_tests']*100:.1f}%)")
print()

print("By Category:")
print("-" * 80)
for category, stats in sorted(test_results["categories"].items()):
    total = stats["passed"] + stats["failed"] + stats["skipped"]
    pass_rate = stats["passed"] / total * 100 if total > 0 else 0
    print(f"{category:20} {stats['passed']:2}/{total:2} passed ({pass_rate:5.1f}%)")

with open("/tmp/mcp_test_results.json", "w") as f:
    json.dump(test_results, f, indent=2)

print()
print("=" * 80)
print(f"Results saved to: /tmp/mcp_test_results.json")
print("=" * 80)
