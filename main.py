from fastapi import FastAPI, HTTPException, Header, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from typing import Dict, Any, Optional
import pandas as pd
import math

from db import get_connection, set_connection_config, get_config, test_connection, clear_session
from profiler import profile_table
from agent.enrichment_agent import ProfileEnrichmentAgent
from models.schema_models import EnrichmentInput, TableProfile, ColumnStats
from mcp import router as mcp_router, PROFILE_STORE
from agent.sql_agent import generate_sql
from utils.sql_executor import execute_sql
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="ChatSQL API", version="2.0.0")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# ──────────────────────────────────────────────────────────────
# CORS — allow any origin (lock down in production if needed)
# ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = ProfileEnrichmentAgent()
app.include_router(mcp_router)


# ──────────────────────────────────────────────────────────────
# SESSION HELPER
# ──────────────────────────────────────────────────────────────
SESSION_COOKIE = "chatsql_session"

def get_or_create_session(request: Request, response: Response) -> str:
    """Return existing session id from cookie, or mint a new one."""
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        session_id = str(uuid4())
        response.set_cookie(
            SESSION_COOKIE,
            session_id,
            max_age=86400 * 7,   # 7 days
            httponly=True,
            samesite="lax",
        )
    return session_id


# ──────────────────────────────────────────────────────────────
# REQUEST MODELS
# ──────────────────────────────────────────────────────────────
class DBConnectRequest(BaseModel):
    host: str
    user: str
    password: str
    database: str
    port: Optional[int] = 3306


class DBConnectResponse(BaseModel):
    status: str
    message: str
    config: Optional[dict] = None
    session_id: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# /connect
# ──────────────────────────────────────────────────────────────
@app.post("/connect", response_model=DBConnectResponse)
def connect_database(req: DBConnectRequest, request: Request, response: Response):
    try:
        test_connection(req.host, req.user, req.password, req.database, req.port)
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")

    session_id = get_or_create_session(request, response)
    set_connection_config(session_id, req.host, req.user, req.password, req.database, req.port)

    return DBConnectResponse(
        status="connected",
        message=f"Successfully connected to '{req.database}' at {req.host}:{req.port}",
        config=get_config(session_id),
        session_id=session_id,
    )


# ──────────────────────────────────────────────────────────────
# /disconnect
# ──────────────────────────────────────────────────────────────
@app.post("/disconnect")
def disconnect(request: Request, response: Response):
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        clear_session(session_id)
        response.delete_cookie(SESSION_COOKIE)
    return {"status": "disconnected"}


# ──────────────────────────────────────────────────────────────
# /connection/status
# ──────────────────────────────────────────────────────────────
@app.get("/connection/status")
def connection_status(request: Request, response: Response):
    session_id = get_or_create_session(request, response)
    cfg = get_config(session_id)
    if cfg is None:
        return {"connected": False, "config": None}
    return {"connected": True, "config": cfg}


# ──────────────────────────────────────────────────────────────
# /tables
# ──────────────────────────────────────────────────────────────
@app.get("/tables")
def list_tables(request: Request, response: Response):
    session_id = get_or_create_session(request, response)
    try:
        conn = get_connection(session_id)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return {"tables": tables}
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────
# /tables/{table_name}/preview
# ──────────────────────────────────────────────────────────────
def _clean(v):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


@app.get("/tables/{table_name}/preview")
def preview_table(table_name: str, request: Request, response: Response, limit: int = 10):
    session_id = get_or_create_session(request, response)
    try:
        conn = get_connection(session_id)
        df = pd.read_sql(f"SELECT * FROM `{table_name}` LIMIT {limit}", conn)
        conn.close()
        df = df.where(pd.notnull(df), None)
        rows = [{k: _clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]
        return {"table_name": table_name, "columns": list(df.columns), "rows": rows, "row_count": len(df)}
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────
# /tables/{table_name}/schema
# ──────────────────────────────────────────────────────────────
@app.get("/tables/{table_name}/schema")
def table_schema(table_name: str, request: Request, response: Response):
    session_id = get_or_create_session(request, response)
    try:
        conn = get_connection(session_id)
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE `{table_name}`")
        columns = [
            {"field": row[0], "type": row[1], "null": row[2], "key": row[3], "default": row[4]}
            for row in cursor.fetchall()
        ]
        conn.close()
        return {"table_name": table_name, "schema": columns}
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────
# /enrich/{table_name}
# ──────────────────────────────────────────────────────────────
@app.get("/enrich/{table_name}")
def enrich_table(table_name: str, request: Request, response: Response, domain: str = "general"):
    session_id = get_or_create_session(request, response)
    try:
        raw_profile = profile_table(table_name, session_id)
        columns = [ColumnStats(**col) for col in raw_profile["columns"]]
        table = TableProfile(
            table_name=raw_profile["table_name"],
            columns=columns,
            sample_values=raw_profile["sample_values"],
        )
        input_data = EnrichmentInput(table=table, domain_hint=domain)
        result = agent.enrich(input_data)
        return {"raw_profile": raw_profile, "ai_enrichment": result}
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────────────────────────
# PROFILE APIs
# ──────────────────────────────────────────────────────────────
@app.post("/profiles")
def create_profile(data: dict, request: Request, response: Response):
    session_id = get_or_create_session(request, response)
    table_name = data.get("table_name")
    if not table_name:
        raise HTTPException(status_code=400, detail="table_name required")

    data_source_ref = data.get("data_source_ref", "default")

    for profile in PROFILE_STORE:
        if (
            profile.get("table_name") == table_name
            and profile.get("data_source_ref") == data_source_ref
        ):
            return {"request_id": profile["request_id"]}

    try:
        raw_profile = profile_table(table_name, session_id)
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    request_id = str(uuid4())
    PROFILE_STORE.append(
        {
            "request_id": request_id,
            "table_name": table_name,
            "data_source_ref": data_source_ref,
            "mode": data.get("mode", "full"),
            "profile": raw_profile,
        }
    )
    return {"request_id": request_id}


@app.get("/profiles/{request_id}")
def get_profile(request_id: str):
    for profile in PROFILE_STORE:
        if profile["request_id"] == request_id:
            return profile
    raise HTTPException(status_code=404, detail="Profile not found")


@app.get("/profiles")
def list_profiles(tenant_id: str = None):
    results = PROFILE_STORE
    if tenant_id:
        results = [r for r in PROFILE_STORE if r.get("data_source_ref", "").lower() == tenant_id.lower()]
        if not results:
            results = PROFILE_STORE
    return {"profiles": results}


# ──────────────────────────────────────────────────────────────
# /ask — NL → SQL
# ──────────────────────────────────────────────────────────────
@app.get("/ask")
def ask(query: str, request: Request, response: Response):
    session_id = get_or_create_session(request, response)
    try:
        sql = generate_sql(query, session_id)
        data = execute_sql(sql, session_id)
        return {"query": query, "sql": sql, "data": data}
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────
# HEALTH / ROOT
# ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "ChatSQL API", "version": "2.0.0"}


@app.get("/")
def serve_ui():
    return FileResponse("frontend/index.html")
