# Test Plan — cli-anything-icepanel

## Test Inventory

- `test_core.py`: ~40 unit tests (synthetic data, no network)
- `test_full_e2e.py`: ~15 E2E tests (real API calls, requires valid API key)

## Unit Test Plan (test_core.py)

### Backend (icepanel_backend.py)
- Config save/load round-trip
- API key resolution (env var priority, missing key error)
- Default org/landscape/version resolution
- File locking on save

### Auth (auth.py)
- setup_api_key stores key and defaults
- set_defaults updates without overwriting key
- logout removes config file
- get_auth_status returns correct structure

### Organizations (organizations.py)
- list_organizations formats response
- get_organization requires org_id
- create_landscape passes correct body
- _require_org_id falls through to default

### Model Objects (model_objects.py)
- create_object builds correct body with kwargs
- update_object rejects empty updates
- _lv resolves defaults correctly

### Connections (connections.py)
- create_connection builds origin/target body
- update_connection rejects empty updates

### Flows (flows.py)
- list_flows formats response
- export functions build correct URLs

### Diagrams (diagrams.py)
- list_diagrams formats response
- exists_diagram interprets HEAD status

### Tags (tags.py)
- list_tags formats with _fmt_tag
- create_tag builds correct body

## E2E Test Plan (test_full_e2e.py)

Requires: `ICEPANEL_API_KEY` env var set with valid key.

### Workflows
1. **Auth validation**: Setup → status check → verify authenticated
2. **Org discovery**: List orgs → get first org → list its landscapes
3. **Object CRUD**: List objects → create → get → update → delete
4. **Connection lifecycle**: Create two objects → connect → get → delete
5. **Flow exploration**: List flows → export mermaid for first flow
6. **Version management**: List versions → create → get → delete
7. **CLI subprocess**: Run `--help`, `--json org list` via subprocess

## Test Results

_Pending — run tests with:_
```bash
python3 -m pytest cli_anything/icepanel/tests/ -v -s
```
