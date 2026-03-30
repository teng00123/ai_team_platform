"""
AI Team Platform - FastAPI 服务（含 SSE 实时推送 + 主控编排 API）
"""
import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from typing import List, Optional
from pathlib import Path

from models import AgentRole, TeamTask, CreateRoleRequest, SendTaskRequest, OrchestrationRequest
from team_manager import TeamManager

app = FastAPI(title="AI Team Platform", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
manager = TeamManager()

# ─── 角色管理 ────────────────────────────────────────────────────

@app.get("/roles", response_model=List[AgentRole])
def list_roles():
    return manager.list_roles()

@app.post("/roles", response_model=AgentRole)
def create_role(req: CreateRoleRequest):
    return manager.add_role(req)

@app.get("/roles/{role_id}", response_model=AgentRole)
def get_role(role_id: str):
    r = manager.get_role(role_id)
    if not r: raise HTTPException(404, "角色不存在")
    return r

@app.put("/roles/{role_id}", response_model=AgentRole)
def update_role(role_id: str, req: CreateRoleRequest):
    r = manager.update_role(role_id, name=req.name, agent_id=req.agent_id,
                             description=req.description, system_prompt=req.system_prompt,
                             is_controller=req.is_controller)
    if not r: raise HTTPException(404, "角色不存在")
    return r

@app.delete("/roles/{role_id}")
def delete_role(role_id: str):
    if not manager.delete_role(role_id): raise HTTPException(404, "角色不存在")
    return {"ok": True}

# ─── 普通任务 ────────────────────────────────────────────────────

@app.get("/tasks", response_model=List[TeamTask])
def list_tasks(role_id: Optional[str] = None):
    return manager.list_tasks(role_id)

@app.get("/tasks/{task_id}", response_model=TeamTask)
def get_task(task_id: str):
    tasks = {t.id: t for t in manager.list_tasks()}
    if task_id not in tasks: raise HTTPException(404, "任务不存在")
    return tasks[task_id]

@app.post("/roles/{role_id}/tasks", response_model=TeamTask)
async def send_task(role_id: str, req: SendTaskRequest):
    try:
        return await manager.send_task(role_id, req.message)
    except ValueError as e:
        raise HTTPException(404, str(e))

# ─── 主控编排 API ────────────────────────────────────────────────

@app.post("/orchestrate", response_model=TeamTask, summary="主控编排任务")
async def orchestrate(req: OrchestrationRequest):
    """
    主控角色接收总任务 → 自动拆解 → 并发下发给子角色 → 汇总结果
    """
    try:
        return await manager.orchestrate(
            controller_id=req.controller_id,
            message=req.message,
            target_role_ids=req.target_role_ids,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.get("/controller", response_model=Optional[AgentRole], summary="获取当前主控角色")
def get_controller():
    return manager.get_controller()

# ─── SSE 实时事件流 ──────────────────────────────────────────────

@app.get("/events", summary="SSE 实时事件推送")
async def event_stream():
    q = manager.subscribe()
    async def generate():
        try:
            yield "data: {\"event\":\"connected\"}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            manager.unsubscribe(q)
    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

# ─── 前端页面 ────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse((Path(__file__).parent/"static"/"index.html").read_text("utf-8"))

@app.get("/scene", response_class=HTMLResponse)
def scene():
    return HTMLResponse((Path(__file__).parent/"static"/"scene.html").read_text("utf-8"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8765, reload=True)
