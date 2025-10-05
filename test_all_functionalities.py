#!/usr/bin/env python3
"""
Comprehensive test script for all Asana Clone API functionalities.
Tests both MCP endpoints and regular HTTP API endpoints.
"""

import requests
import json
from datetime import datetime
from typing import Any

BASE_URL = "http://localhost:8000"
MCP_BASE_URL = f"{BASE_URL}/mcp-api/mcp"

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.total = 0

    def add_pass(self, test_name: str, details: str = ""):
        self.total += 1
        self.passed.append({"test": test_name, "details": details})
        print(f"✓ PASS: {test_name}")
        if details:
            print(f"  {details}")

    def add_fail(self, test_name: str, error: str):
        self.total += 1
        self.failed.append({"test": test_name, "error": error})
        print(f"✗ FAIL: {test_name}")
        print(f"  Error: {error}")

    def summary(self):
        return {
            "total_tests": self.total,
            "passed": len(self.passed),
            "failed": len(self.failed),
            "pass_rate": f"{(len(self.passed) / self.total * 100):.1f}%" if self.total > 0 else "0%",
            "passed_tests": self.passed,
            "failed_tests": self.failed
        }

results = TestResults()
test_data = {}  # Store created resources

def test_mcp_health():
    """Test MCP health check"""
    try:
        response = requests.get(f"{MCP_BASE_URL}/health")
        if response.status_code == 200 and response.json().get("status") == "ok":
            results.add_pass("MCP Health Check", f"Status: {response.json()}")
        else:
            results.add_fail("MCP Health Check", f"Unexpected response: {response.status_code}")
    except Exception as e:
        results.add_fail("MCP Health Check", str(e))

def test_mcp_register():
    """Test MCP user registration"""
    try:
        payload = {
            "email": f"mcp_test_{datetime.now().timestamp()}@example.com",
            "name": "MCP Test User",
            "password": "testpass123"
        }
        response = requests.post(f"{MCP_BASE_URL}/auth/register", json=payload)
        if response.status_code == 200:
            data = response.json()
            test_data["mcp_token"] = data["token"]
            test_data["mcp_user_id"] = data["user_id"]
            results.add_pass("MCP User Registration", f"User ID: {data['user_id']}")
        else:
            results.add_fail("MCP User Registration", f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        results.add_fail("MCP User Registration", str(e))

def test_mcp_login():
    """Test MCP user login"""
    try:
        # First register a user
        email = f"mcp_login_test_{datetime.now().timestamp()}@example.com"
        password = "logintest123"

        register_payload = {
            "email": email,
            "name": "MCP Login Test",
            "password": password
        }
        requests.post(f"{MCP_BASE_URL}/auth/register", json=register_payload)

        # Now try to login
        login_payload = {
            "email": email,
            "password": password
        }
        response = requests.post(f"{MCP_BASE_URL}/auth/login", json=login_payload)
        if response.status_code == 200:
            data = response.json()
            results.add_pass("MCP User Login", f"Token received for {data['email']}")
        else:
            results.add_fail("MCP User Login", f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        results.add_fail("MCP User Login", str(e))

def test_mcp_create_workspace():
    """Test MCP workspace creation"""
    try:
        if "mcp_token" not in test_data:
            results.add_fail("MCP Create Workspace", "No token available (registration may have failed)")
            return

        payload = {
            "name": f"MCP Test Workspace {datetime.now().timestamp()}",
            "auth_token": test_data["mcp_token"]
        }
        response = requests.post(f"{MCP_BASE_URL}/workspaces", json=payload)
        if response.status_code == 200:
            data = response.json()
            test_data["mcp_workspace_id"] = data["id"]
            results.add_pass("MCP Create Workspace", f"Workspace ID: {data['id']}, Name: {data['name']}")
        else:
            results.add_fail("MCP Create Workspace", f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        results.add_fail("MCP Create Workspace", str(e))

def test_http_register():
    """Test HTTP user registration"""
    try:
        payload = {
            "email": f"http_test_{datetime.now().timestamp()}@example.com",
            "name": "HTTP Test User",
            "password": "httptest123"
        }
        response = requests.post(f"{BASE_URL}/auth/register", json=payload)
        if response.status_code == 201:
            data = response.json()
            test_data["http_token"] = data["token"]
            test_data["http_user"] = data["user"]
            results.add_pass("HTTP User Registration", f"User ID: {data['user']['id']}")
        else:
            results.add_fail("HTTP User Registration", f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        results.add_fail("HTTP User Registration", str(e))

def test_http_login():
    """Test HTTP user login"""
    try:
        # Use the registered user
        email = f"http_login_{datetime.now().timestamp()}@example.com"
        password = "loginpass123"

        # Register first
        register_payload = {
            "email": email,
            "name": "HTTP Login Test",
            "password": password
        }
        requests.post(f"{BASE_URL}/auth/register", json=register_payload)

        # Login
        login_payload = {
            "email": email,
            "password": password
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
        if response.status_code == 200:
            data = response.json()
            results.add_pass("HTTP User Login", f"Logged in as {data['user']['email']}")
        else:
            results.add_fail("HTTP User Login", f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        results.add_fail("HTTP User Login", str(e))

def get_auth_headers():
    """Get authorization headers for HTTP requests"""
    if "http_token" not in test_data:
        return {}
    return {"Authorization": f"Bearer {test_data['http_token']}"}

def test_workspace_crud():
    """Test workspace CRUD operations"""
    headers = get_auth_headers()
    if not headers:
        results.add_fail("Workspace CRUD", "No auth token available")
        return

    # Create
    try:
        payload = {"name": f"Test Workspace {datetime.now().timestamp()}"}
        response = requests.post(f"{BASE_URL}/workspaces", json=payload, headers=headers)
        if response.status_code == 201:
            workspace = response.json()
            test_data["workspace_id"] = workspace["id"]
            results.add_pass("Workspace Create", f"ID: {workspace['id']}")
        else:
            results.add_fail("Workspace Create", f"Status: {response.status_code}")
            return
    except Exception as e:
        results.add_fail("Workspace Create", str(e))
        return

    # Read
    try:
        response = requests.get(f"{BASE_URL}/workspaces/{test_data['workspace_id']}", headers=headers)
        if response.status_code == 200:
            results.add_pass("Workspace Read", f"Name: {response.json()['name']}")
        else:
            results.add_fail("Workspace Read", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Workspace Read", str(e))

    # Update
    try:
        payload = {"name": "Updated Workspace Name"}
        response = requests.patch(f"{BASE_URL}/workspaces/{test_data['workspace_id']}", json=payload, headers=headers)
        if response.status_code == 200:
            results.add_pass("Workspace Update", f"New name: {response.json()['name']}")
        else:
            results.add_fail("Workspace Update", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Workspace Update", str(e))

    # List
    try:
        response = requests.get(f"{BASE_URL}/workspaces", headers=headers)
        if response.status_code == 200:
            workspaces = response.json()
            results.add_pass("Workspace List", f"Found {len(workspaces)} workspaces")
        else:
            results.add_fail("Workspace List", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Workspace List", str(e))

def test_project_crud():
    """Test project CRUD operations"""
    headers = get_auth_headers()
    if not headers or "workspace_id" not in test_data:
        results.add_fail("Project CRUD", "Missing auth or workspace")
        return

    # Create
    try:
        payload = {
            "name": "Test Project",
            "description": "A test project",
            "workspace_id": test_data["workspace_id"]
        }
        response = requests.post(f"{BASE_URL}/projects", json=payload, headers=headers)
        if response.status_code == 201:
            project = response.json()
            test_data["project_id"] = project["id"]
            results.add_pass("Project Create", f"ID: {project['id']}")
        else:
            results.add_fail("Project Create", f"Status: {response.status_code}, Body: {response.text}")
            return
    except Exception as e:
        results.add_fail("Project Create", str(e))
        return

    # Read
    try:
        response = requests.get(f"{BASE_URL}/projects/{test_data['project_id']}", headers=headers)
        if response.status_code == 200:
            results.add_pass("Project Read", f"Name: {response.json()['name']}")
        else:
            results.add_fail("Project Read", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Project Read", str(e))

    # Update
    try:
        payload = {"name": "Updated Project"}
        response = requests.patch(f"{BASE_URL}/projects/{test_data['project_id']}", json=payload, headers=headers)
        if response.status_code == 200:
            results.add_pass("Project Update", f"New name: {response.json()['name']}")
        else:
            results.add_fail("Project Update", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Project Update", str(e))

    # List
    try:
        response = requests.get(f"{BASE_URL}/projects?workspace_id={test_data['workspace_id']}", headers=headers)
        if response.status_code == 200:
            results.add_pass("Project List", f"Found {len(response.json())} projects")
        else:
            results.add_fail("Project List", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Project List", str(e))

def test_task_crud():
    """Test task CRUD operations"""
    headers = get_auth_headers()
    if not headers or "project_id" not in test_data:
        results.add_fail("Task CRUD", "Missing auth or project")
        return

    # Create
    try:
        payload = {
            "name": "Test Task",
            "description": "A test task",
            "project_id": test_data["project_id"]
        }
        response = requests.post(f"{BASE_URL}/tasks", json=payload, headers=headers)
        if response.status_code == 201:
            task = response.json()
            test_data["task_id"] = task["id"]
            results.add_pass("Task Create", f"ID: {task['id']}")
        else:
            results.add_fail("Task Create", f"Status: {response.status_code}, Body: {response.text}")
            return
    except Exception as e:
        results.add_fail("Task Create", str(e))
        return

    # Read
    try:
        response = requests.get(f"{BASE_URL}/tasks/{test_data['task_id']}", headers=headers)
        if response.status_code == 200:
            results.add_pass("Task Read", f"Name: {response.json()['name']}")
        else:
            results.add_fail("Task Read", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Task Read", str(e))

    # Update
    try:
        payload = {"name": "Updated Task", "completed": True}
        response = requests.patch(f"{BASE_URL}/tasks/{test_data['task_id']}", json=payload, headers=headers)
        if response.status_code == 200:
            results.add_pass("Task Update", f"Completed: {response.json()['completed']}")
        else:
            results.add_fail("Task Update", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Task Update", str(e))

    # List
    try:
        response = requests.get(f"{BASE_URL}/tasks?project_id={test_data['project_id']}", headers=headers)
        if response.status_code == 200:
            results.add_pass("Task List", f"Found {response.json()['total']} tasks")
        else:
            results.add_fail("Task List", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Task List", str(e))

def test_comment_operations():
    """Test comment operations"""
    headers = get_auth_headers()
    if not headers or "task_id" not in test_data:
        results.add_fail("Comment Operations", "Missing auth or task")
        return

    # Create comment
    try:
        payload = {"text": "This is a test comment"}
        response = requests.post(f"{BASE_URL}/tasks/{test_data['task_id']}/comments", json=payload, headers=headers)
        if response.status_code == 201:
            comment = response.json()
            test_data["comment_id"] = comment["id"]
            results.add_pass("Comment Create", f"ID: {comment['id']}")
        else:
            results.add_fail("Comment Create", f"Status: {response.status_code}")
            return
    except Exception as e:
        results.add_fail("Comment Create", str(e))
        return

    # List comments
    try:
        response = requests.get(f"{BASE_URL}/tasks/{test_data['task_id']}/comments", headers=headers)
        if response.status_code == 200:
            results.add_pass("Comment List", f"Found {len(response.json())} comments")
        else:
            results.add_fail("Comment List", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Comment List", str(e))

    # Update comment
    try:
        payload = {"text": "Updated comment text"}
        response = requests.patch(f"{BASE_URL}/comments/{test_data['comment_id']}", json=payload, headers=headers)
        if response.status_code == 200:
            results.add_pass("Comment Update", "Comment updated successfully")
        else:
            results.add_fail("Comment Update", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Comment Update", str(e))

def test_tag_operations():
    """Test tag operations"""
    headers = get_auth_headers()
    if not headers or "workspace_id" not in test_data or "task_id" not in test_data:
        results.add_fail("Tag Operations", "Missing auth, workspace or task")
        return

    # Create tag
    try:
        payload = {
            "name": "urgent",
            "workspace_id": test_data["workspace_id"]
        }
        response = requests.post(f"{BASE_URL}/tags", json=payload, headers=headers)
        if response.status_code == 201:
            tag = response.json()
            test_data["tag_id"] = tag["id"]
            results.add_pass("Tag Create", f"ID: {tag['id']}")
        else:
            results.add_fail("Tag Create", f"Status: {response.status_code}")
            return
    except Exception as e:
        results.add_fail("Tag Create", str(e))
        return

    # Add tag to task
    try:
        response = requests.post(f"{BASE_URL}/tasks/{test_data['task_id']}/tags/{test_data['tag_id']}", headers=headers)
        if response.status_code == 204:
            results.add_pass("Tag Add to Task", "Tag added successfully")
        else:
            results.add_fail("Tag Add to Task", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Tag Add to Task", str(e))

    # List tags
    try:
        response = requests.get(f"{BASE_URL}/tags?workspace_id={test_data['workspace_id']}", headers=headers)
        if response.status_code == 200:
            results.add_pass("Tag List", f"Found {len(response.json())} tags")
        else:
            results.add_fail("Tag List", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Tag List", str(e))

def test_section_operations():
    """Test section operations"""
    headers = get_auth_headers()
    if not headers or "project_id" not in test_data:
        results.add_fail("Section Operations", "Missing auth or project")
        return

    # Create section
    try:
        payload = {
            "name": "To Do",
            "project_id": test_data["project_id"]
        }
        response = requests.post(f"{BASE_URL}/sections", json=payload, headers=headers)
        if response.status_code == 201:
            section = response.json()
            test_data["section_id"] = section["id"]
            results.add_pass("Section Create", f"ID: {section['id']}")
        else:
            results.add_fail("Section Create", f"Status: {response.status_code}")
            return
    except Exception as e:
        results.add_fail("Section Create", str(e))
        return

    # List sections
    try:
        response = requests.get(f"{BASE_URL}/sections?project_id={test_data['project_id']}", headers=headers)
        if response.status_code == 200:
            results.add_pass("Section List", f"Found {len(response.json())} sections")
        else:
            results.add_fail("Section List", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Section List", str(e))

    # Update section
    try:
        payload = {"name": "In Progress"}
        response = requests.patch(f"{BASE_URL}/sections/{test_data['section_id']}", json=payload, headers=headers)
        if response.status_code == 200:
            results.add_pass("Section Update", "Section updated successfully")
        else:
            results.add_fail("Section Update", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Section Update", str(e))

def test_team_operations():
    """Test team operations"""
    headers = get_auth_headers()
    if not headers or "workspace_id" not in test_data:
        results.add_fail("Team Operations", "Missing auth or workspace")
        return

    # Create team
    try:
        payload = {
            "name": "Engineering Team",
            "workspace_id": test_data["workspace_id"]
        }
        response = requests.post(f"{BASE_URL}/teams", json=payload, headers=headers)
        if response.status_code == 201:
            team = response.json()
            test_data["team_id"] = team["id"]
            results.add_pass("Team Create", f"ID: {team['id']}")
        else:
            results.add_fail("Team Create", f"Status: {response.status_code}")
            return
    except Exception as e:
        results.add_fail("Team Create", str(e))
        return

    # List teams
    try:
        response = requests.get(f"{BASE_URL}/teams?workspace_id={test_data['workspace_id']}", headers=headers)
        if response.status_code == 200:
            results.add_pass("Team List", f"Found {len(response.json())} teams")
        else:
            results.add_fail("Team List", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Team List", str(e))

def test_user_operations():
    """Test user operations"""
    headers = get_auth_headers()
    if not headers:
        results.add_fail("User Operations", "Missing auth")
        return

    # Get current user
    try:
        response = requests.get(f"{BASE_URL}/users/me", headers=headers)
        if response.status_code == 200:
            user = response.json()
            results.add_pass("Get Current User", f"Email: {user['email']}")
        else:
            results.add_fail("Get Current User", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Get Current User", str(e))

    # Get user by ID
    try:
        if "http_user" in test_data:
            user_id = test_data["http_user"]["id"]
            response = requests.get(f"{BASE_URL}/users/{user_id}", headers=headers)
            if response.status_code == 200:
                results.add_pass("Get User by ID", f"Name: {response.json()['name']}")
            else:
                results.add_fail("Get User by ID", f"Status: {response.status_code}")
    except Exception as e:
        results.add_fail("Get User by ID", str(e))

def cleanup():
    """Delete created resources (optional cleanup)"""
    headers = get_auth_headers()
    if not headers:
        return

    # Delete in reverse order of dependencies
    if "comment_id" in test_data:
        try:
            requests.delete(f"{BASE_URL}/comments/{test_data['comment_id']}", headers=headers)
        except:
            pass

    if "task_id" in test_data:
        try:
            requests.delete(f"{BASE_URL}/tasks/{test_data['task_id']}", headers=headers)
        except:
            pass

    if "section_id" in test_data:
        try:
            requests.delete(f"{BASE_URL}/sections/{test_data['section_id']}", headers=headers)
        except:
            pass

    if "tag_id" in test_data:
        try:
            requests.delete(f"{BASE_URL}/tags/{test_data['tag_id']}", headers=headers)
        except:
            pass

    if "project_id" in test_data:
        try:
            requests.delete(f"{BASE_URL}/projects/{test_data['project_id']}", headers=headers)
        except:
            pass

    if "workspace_id" in test_data:
        try:
            requests.delete(f"{BASE_URL}/workspaces/{test_data['workspace_id']}", headers=headers)
        except:
            pass

if __name__ == "__main__":
    print("=" * 80)
    print("ASANA CLONE API - COMPREHENSIVE FUNCTIONALITY TEST")
    print("=" * 80)
    print()

    print("Testing MCP Endpoints...")
    print("-" * 80)
    test_mcp_health()
    test_mcp_register()
    test_mcp_login()
    test_mcp_create_workspace()
    print()

    print("Testing HTTP API Endpoints...")
    print("-" * 80)
    test_http_register()
    test_http_login()
    test_workspace_crud()
    test_project_crud()
    test_task_crud()
    test_comment_operations()
    test_tag_operations()
    test_section_operations()
    test_team_operations()
    test_user_operations()
    print()

    print("Cleaning up...")
    cleanup()
    print()

    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    summary = results.summary()
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Pass Rate: {summary['pass_rate']}")
    print()

    if summary['failed_tests']:
        print("Failed Tests:")
        for fail in summary['failed_tests']:
            print(f"  - {fail['test']}: {fail['error']}")
        print()

    # Save results to JSON
    with open('test_results.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print("Detailed results saved to test_results.json")

    # Exit with appropriate code
    exit(0 if summary['failed'] == 0 else 1)
