"""
AI Team Platform - FastAPI Web 服务
提供 REST API 管理 AI 团队角色和任务
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import List, Optional

from models import AgentRole, TeamTask, CreateRoleRequest, SendTaskRequest
from team_manager import TeamManager

app = FastAPI(title="AI Team Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = TeamManager()


# ─────────────────────────── 角色管理 API ───────────────────────────

@app.get("/roles", response_model=List[AgentRole], summary="获取所有团队角色")
def list_roles():
    return manager.list_roles()


@app.post("/roles", response_model=AgentRole, summary="新增角色")
def create_role(req: CreateRoleRequest):
    return manager.add_role(req)


@app.get("/roles/{role_id}", response_model=AgentRole, summary="获取单个角色")
def get_role(role_id: str):
    role = manager.get_role(role_id)
    if not role:
        raise HTTPException(404, "角色不存在")
    return role


@app.put("/roles/{role_id}", response_model=AgentRole, summary="更新角色")
def update_role(role_id: str, req: CreateRoleRequest):
    role = manager.update_role(
        role_id,
        name=req.name,
        agent_id=req.agent_id,
        description=req.description,
        system_prompt=req.system_prompt,
    )
    if not role:
        raise HTTPException(404, "角色不存在")
    return role


@app.delete("/roles/{role_id}", summary="删除角色")
def delete_role(role_id: str):
    if not manager.delete_role(role_id):
        raise HTTPException(404, "角色不存在")
    return {"message": f"角色 {role_id} 已删除"}


# ─────────────────────────── 任务 API ───────────────────────────────

@app.get("/tasks", response_model=List[TeamTask], summary="获取所有任务")
def list_tasks(role_id: Optional[str] = None):
    return manager.list_tasks(role_id)


@app.post("/roles/{role_id}/tasks", response_model=TeamTask, summary="向角色发送任务")
async def send_task(role_id: str, req: SendTaskRequest):
    try:
        return await manager.send_task(role_id, req.message)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"任务执行失败: {e}")


# ─────────────────────────── 简易 Web UI ────────────────────────────

@app.get("/", response_class=HTMLResponse, summary="Web 管理界面")
def index():
    return """
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI Team Platform</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #0f172a; color: #e2e8f0; min-height: 100vh; }
    header { background: #1e293b; padding: 16px 32px; display: flex;
             align-items: center; gap: 12px; border-bottom: 1px solid #334155; }
    header h1 { font-size: 1.4rem; font-weight: 700; color: #38bdf8; }
    .badge { background: #0ea5e9; color: #fff; font-size: 0.7rem;
             padding: 2px 8px; border-radius: 999px; font-weight: 600; }
    .container { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    .card { background: #1e293b; border-radius: 12px; padding: 24px;
            border: 1px solid #334155; }
    .card h2 { font-size: 1rem; font-weight: 600; color: #94a3b8;
               text-transform: uppercase; letter-spacing: .05em; margin-bottom: 16px; }
    input, textarea, select { width: 100%; background: #0f172a; border: 1px solid #334155;
      color: #e2e8f0; border-radius: 8px; padding: 10px 14px; font-size: 0.9rem;
      margin-bottom: 10px; outline: none; }
    input:focus, textarea:focus { border-color: #38bdf8; }
    button { background: #0ea5e9; color: #fff; border: none; padding: 10px 20px;
             border-radius: 8px; cursor: pointer; font-size: 0.9rem; font-weight: 600;
             transition: background .2s; }
    button:hover { background: #0284c7; }
    button.danger { background: #ef4444; }
    button.danger:hover { background: #dc2626; }
    button.ghost { background: #334155; }
    button.ghost:hover { background: #475569; }
    .role-list { display: flex; flex-direction: column; gap: 10px; }
    .role-item { background: #0f172a; border-radius: 8px; padding: 14px 16px;
                 border: 1px solid #334155; display: flex; justify-content: space-between;
                 align-items: center; }
    .role-name { font-weight: 600; color: #38bdf8; }
    .role-desc { font-size: 0.8rem; color: #64748b; margin-top: 2px; }
    .role-agent { font-size: 0.75rem; background: #1e293b; border: 1px solid #334155;
                  padding: 2px 8px; border-radius: 999px; color: #94a3b8; }
    .actions { display: flex; gap: 8px; }
    .task-result { background: #0f172a; border: 1px solid #334155; border-radius: 8px;
                   padding: 14px; font-size: 0.85rem; color: #a8c7fa;
                   white-space: pre-wrap; max-height: 200px; overflow-y: auto;
                   margin-top: 12px; display: none; }
    .status { font-size: 0.8rem; padding: 2px 8px; border-radius: 999px;
              font-weight: 600; display: inline-block; margin-top: 6px; }
    .status.done { background: #065f46; color: #6ee7b7; }
    .status.running { background: #1e3a8a; color: #93c5fd; }
    .status.failed { background: #7f1d1d; color: #fca5a5; }
    .empty { color: #475569; font-size: 0.9rem; text-align: center; padding: 20px; }
    .spinner { display: inline-block; width: 16px; height: 16px;
               border: 2px solid #334155; border-top-color: #38bdf8;
               border-radius: 50%; animation: spin .6s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <header>
    <h1>🤖 AI Team Platform</h1>
    <span class="badge">OpenClaw Agents</span>
  </header>

  <div class="container">
    <div class="grid">

      <!-- 左：角色列表 -->
      <div>
        <div class="card">
          <h2>团队成员</h2>
          <div id="roles-list" class="role-list">
            <div class="empty">加载中…</div>
          </div>
        </div>

        <!-- 发送任务 -->
        <div class="card" style="margin-top:24px">
          <h2>发送任务</h2>
          <select id="task-role-select"><option value="">选择角色…</option></select>
          <textarea id="task-message" rows="4" placeholder="输入任务内容…"></textarea>
          <button onclick="sendTask()">🚀 发送</button>
          <div id="task-result" class="task-result"></div>
        </div>
      </div>

      <!-- 右：新增角色 -->
      <div>
        <div class="card">
          <h2>新增角色</h2>
          <input id="new-name" placeholder="角色名称（如：产品经理）" />
          <input id="new-agent-id" placeholder="Agent ID（默认: main）" value="main" />
          <input id="new-desc" placeholder="角色描述" />
          <textarea id="new-prompt" rows="4"
            placeholder="系统提示词（可选）&#10;例：你是一名资深产品经理，擅长需求分析和竞品分析。"></textarea>
          <button onclick="addRole()">➕ 新增角色</button>
        </div>
      </div>

    </div>
  </div>

<script>
const API = '';

async function loadRoles() {
  const res = await fetch(`${API}/roles`);
  const roles = await res.json();
  const list = document.getElementById('roles-list');
  const sel = document.getElementById('task-role-select');

  // clear select (keep first option)
  sel.innerHTML = '<option value="">选择角色…</option>';

  if (!roles.length) {
    list.innerHTML = '<div class="empty">暂无团队成员，先新增一个角色吧</div>';
    return;
  }

  list.innerHTML = roles.map(r => `
    <div class="role-item" id="role-${r.id}">
      <div>
        <div class="role-name">${r.name}</div>
        <div class="role-desc">${r.description || '暂无描述'}</div>
        <span class="role-agent">agent: ${r.agent_id}</span>
      </div>
      <div class="actions">
        <button class="danger" onclick="deleteRole('${r.id}')">删除</button>
      </div>
    </div>
  `).join('');

  roles.forEach(r => {
    const opt = document.createElement('option');
    opt.value = r.id;
    opt.textContent = r.name;
    sel.appendChild(opt);
  });
}

async function addRole() {
  const name = document.getElementById('new-name').value.trim();
  const agentId = document.getElementById('new-agent-id').value.trim() || 'main';
  const desc = document.getElementById('new-desc').value.trim();
  const prompt = document.getElementById('new-prompt').value.trim();
  if (!name) { alert('请填写角色名称'); return; }

  await fetch(`${API}/roles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, agent_id: agentId, description: desc, system_prompt: prompt })
  });

  document.getElementById('new-name').value = '';
  document.getElementById('new-desc').value = '';
  document.getElementById('new-prompt').value = '';
  await loadRoles();
}

async function deleteRole(id) {
  if (!confirm('确认删除该角色？')) return;
  await fetch(`${API}/roles/${id}`, { method: 'DELETE' });
  await loadRoles();
}

async function sendTask() {
  const roleId = document.getElementById('task-role-select').value;
  const msg = document.getElementById('task-message').value.trim();
  if (!roleId) { alert('请选择角色'); return; }
  if (!msg) { alert('请输入任务内容'); return; }

  const resultBox = document.getElementById('task-result');
  resultBox.style.display = 'block';
  resultBox.innerHTML = '<span class="spinner"></span>  正在处理任务…';

  const res = await fetch(`${API}/roles/${roleId}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg })
  });
  const task = await res.json();

  const statusClass = task.status === 'done' ? 'done' : task.status === 'failed' ? 'failed' : 'running';
  resultBox.innerHTML = `
    <span class="status ${statusClass}">${task.status}</span>
    <div style="margin-top:8px">${task.result || '（无结果）'}</div>
  `;
}

loadRoles();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8765, reload=True)
