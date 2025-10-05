# Known Issues

- `pytest` currently hangs after ~60s when running `tests/test_api.py::test_full_api_flow` even with `ENABLE_MCP=0`. The run stalls before the first request completes, matching the earlier recursion loop encountered inside `fastapi_mcp.openapi.utils.resolve_schema_references`. We need to either bypass MCP startup during tests or trim the OpenAPI content passed to `FastApiMCP` so schema resolution stops recursing.
- Because the hang blocks the suite, we could not confirm that recent MCP integration changes are safe. Before merging we should add a regression test that imports `app.main` with MCP disabled and spins up a `TestClient` to guard against this issue.
- `tests/test_api.py` still contains temporary `print(...)` debug statements from the prior investigation. Once the hang is resolved they should be removed to keep the test output quiet.

## Reproduction

```bash
cd /workspaces/asana_clone
ENABLE_MCP=0 pytest tests/test_api.py::test_full_api_flow -vv -s
```
This command consistently times out after 120 seconds.
