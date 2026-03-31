"""
AI Team Platform - FastAPI 服务（含 SSE 实时推送 + 主控编排 API）
"""
import asyncio
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from pathlib import Path

from models import AgentRole, TeamTask, CreateRoleRequest, SendTaskRequest, OrchestrationRequest
from team_manager import TeamManager

app = FastAPI(title="AI Team Platform", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 挂载静态资源目录（vendor JS 等）
_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

manager = TeamManager()

# ─── 角色管理 ────────────────────────────────────────────────────

@app.get("/roles", response_model=List[AgentRole])
def list_roles():
    return manager.list_roles()

@app.post("/roles", response_model=AgentRole)
async def create_role(req: CreateRoleRequest, background_tasks: "BackgroundTasks"):
    role = manager.add_role_sync(req)  # 同步创建，不含 session
    background_tasks.add_task(manager._init_role_session, role.id)
    return role

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

@app.post("/roles/{role_id}/init-session", summary="初始化/重置角色持久 session")
async def init_role_session(role_id: str):
    """手动触发为角色创建新的持久化 session"""
    r = manager.get_role(role_id)
    if not r:
        raise HTTPException(404, "角色不存在")
    asyncio.create_task(manager._init_role_session(role_id))
    return {"ok": True, "message": f"正在为「{r.name}」初始化持久 session，约需10-15秒"}

@app.delete("/roles/{role_id}", summary="删除角色")
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

@app.get("/tasks/{task_id}/sub/{role_id}")
def get_sub_task(task_id: str, role_id: str):
    """获取编排任务中某个角色的子任务详情（含完整结果）"""
    tasks = {t.id: t for t in manager.list_tasks()}
    if task_id not in tasks:
        raise HTTPException(404, "任务不存在")
    task = tasks[task_id]
    for st in task.sub_tasks:
        if st.role_id == role_id:
            return st
    raise HTTPException(404, "子任务不存在")

@app.post("/roles/{role_id}/tasks", response_model=TeamTask)
async def send_task(role_id: str, req: SendTaskRequest):
    try:
        return await manager.send_task(role_id, req.message)
    except ValueError as e:
        raise HTTPException(404, str(e))

# ─── 主控编排 API ────────────────────────────────────────────────

@app.post("/orchestrate", summary="主控编排任务（异步，立即返回 task_id）")
async def orchestrate(req: OrchestrationRequest):
    """
    立即返回 task_id，后台异步执行编排全流程。
    前端通过 SSE /events 实时接收进度，或 GET /tasks/{id} 轮询状态。
    """
    try:
        task = await manager.orchestrate_async(
            controller_id=req.controller_id,
            message=req.message,
            target_role_ids=req.target_role_ids,
            generate_code=req.generate_code,
        )
        return {"ok": True, "task_id": task.id, "status": task.status, "message": task.message}
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
