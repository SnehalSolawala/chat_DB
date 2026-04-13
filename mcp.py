from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, List
from uuid import uuid4

router = APIRouter()

# ✅ SINGLE SHARED STORE (LIST)
PROFILE_STORE: List[Dict[str, Any]] = []

# Session cookie name — must match main.py
SESSION_COOKIE = "chatsql_session"
SESSION_HEADER = "X-Session-ID"


# =========================================================
# MCP TOOL: profile_table
# =========================================================
@router.post("/mcp/tools/profile_table")
def mcp_profile_table(data: dict, request: Request):
    """Standalone — does NOT import from main.py to avoid circular deps."""
    from profiler import profile_table
    from db import get_config

    session_id = request.headers.get(SESSION_HEADER) or request.cookies.get(SESSION_COOKIE)
    if not session_id:
        raise HTTPException(status_code=401, detail="No session cookie. Please connect first.")

    table_name = data.get("table_name")
    if not table_name:
        raise HTTPException(status_code=400, detail="table_name required")

    data_source_ref = data.get("data_source_ref", "default")

    # Return existing profile if already computed
    for profile in PROFILE_STORE:
        if (profile.get("table_name") == table_name
                and profile.get("data_source_ref") == data_source_ref):
            return {"request_id": profile["request_id"]}

    try:
        raw_profile = profile_table(table_name, session_id)
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    request_id = str(uuid4())
    PROFILE_STORE.append({
        "request_id": request_id,
        "table_name": table_name,
        "data_source_ref": data_source_ref,
        "mode": data.get("mode", "full"),
        "profile": raw_profile,
    })
    return {"request_id": request_id}


# =========================================================
# MCP TOOL: get_profile
# =========================================================
@router.get("/mcp/tools/get_profile")
def mcp_get_profile(request_id: str):
    for profile in PROFILE_STORE:
        if profile["request_id"] == request_id:
            return profile
    raise HTTPException(status_code=404, detail="Profile not found")


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