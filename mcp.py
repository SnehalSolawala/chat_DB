from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter()

# ✅ SINGLE SHARED STORE (LIST)
PROFILE_STORE: List[Dict[str, Any]] = []


# =========================================================
# MCP TOOL: profile_table
# =========================================================
@router.post("/mcp/tools/profile_table")
def mcp_profile_table(data: dict):
    from main import create_profile
    return create_profile(data)


# =========================================================
# MCP TOOL: get_profile
# =========================================================
@router.get("/mcp/tools/get_profile")
def mcp_get_profile(request_id: str):
    from main import get_profile
    return get_profile(request_id)


# =========================================================
# MCP TOOL: list_profiles
# =========================================================
@router.get("/mcp/tools/list_profiles")
def mcp_list_profiles(tenant_id: str = None):

    print("Tenant ID:", tenant_id)
    print("Total Profiles:", len(PROFILE_STORE))

    # ✅ Filter
    if tenant_id:
        filtered = [
            p for p in PROFILE_STORE
            if p.get("data_source_ref", "").lower() == tenant_id.lower()
        ]
    else:
        filtered = PROFILE_STORE

    # ✅ Fallback (avoid empty result)
    if not filtered:
        filtered = PROFILE_STORE

    # ✅ Keep only latest per table
    latest_profiles = {}
    for p in filtered:
        key = (p.get("data_source_ref"), p.get("table_name"))
        latest_profiles[key] = p

    return {"profiles": list(latest_profiles.values())}


# =========================================================
# MCP TOOL METADATA
# =========================================================
@router.get("/mcp/tools")
def list_mcp_tools():
    return {
        "tools": [
            {
                "name": "profile_table",
                "description": "Create a profile for a database table",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data_source_ref": {"type": "string"},
                        "table_name": {"type": "string"},
                        "mode": {"type": "string"}
                    },
                    "required": ["table_name"]
                }
            },
            {
                "name": "get_profile",
                "description": "Get profiling results using request_id",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request_id": {"type": "string"}
                    },
                    "required": ["request_id"]
                }
            },
            {
                "name": "list_profiles",
                "description": "List previously generated profiles",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tenant_id": {"type": "string"}
                    }
                }
            }
        ]
    }