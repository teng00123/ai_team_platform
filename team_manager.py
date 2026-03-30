"""
AI Team Platform - 团队管理器
负责角色的 CRUD 和与 OpenClaw Agent 的通信
"""
import json
import httpx
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from models import AgentRole, TeamTask, CreateRoleRequest

# 持久化文件
DATA_DIR = Path(__file__).parent / "data"
ROLES_FILE = DATA_DIR / "roles.json"
TASKS_FILE = DATA_DIR / "tasks.json"

# OpenClaw Gateway API（本地）
OPENCLAW_API = "http://localhost:55000"


class TeamManager:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self._roles: Dict[str, AgentRole] = {}
        self._tasks: Dict[str, TeamTask] = {}
        self._load()

    # ──────────────────────────── 持久化 ────────────────────────────

    def _load(self):
        if ROLES_FILE.exists():
            raw = json.loads(ROLES_FILE.read_text())
            self._roles = {k: AgentRole(**v) for k, v in raw.items()}
        if TASKS_FILE.exists():
            raw = json.loads(TASKS_FILE.read_text())
            self._tasks = {k: TeamTask(**v) for k, v in raw.items()}

    def _save(self):
        ROLES_FILE.write_text(
            json.dumps({k: v.model_dump() for k, v in self._roles.items()},
                       default=str, ensure_ascii=False, indent=2)
        )
        TASKS_FILE.write_text(
            json.dumps({k: v.model_dump() for k, v in self._tasks.items()},
                       default=str, ensure_ascii=False, indent=2)
        )

    # ──────────────────────────── 角色管理 ───────────────────────────

    def list_roles(self) -> List[AgentRole]:
        return list(self._roles.values())

    def get_role(self, role_id: str) -> Optional[AgentRole]:
        return self._roles.get(role_id)

    def add_role(self, req: CreateRoleRequest) -> AgentRole:
        role = AgentRole(
            name=req.name,
            agent_id=req.agent_id,
            description=req.description,
            system_prompt=req.system_prompt,
        )
        self._roles[role.id] = role
        self._save()
        return role

    def delete_role(self, role_id: str) -> bool:
        if role_id not in self._roles:
            return False
        del self._roles[role_id]
        self._save()
        return True

    def update_role(self, role_id: str, **kwargs) -> Optional[AgentRole]:
        role = self._roles.get(role_id)
        if not role:
            return None
        updated = role.model_copy(update=kwargs)
        self._roles[role_id] = updated
        self._save()
        return updated

    # ──────────────────────────── 任务调度 ───────────────────────────

    def list_tasks(self, role_id: Optional[str] = None) -> List[TeamTask]:
        tasks = list(self._tasks.values())
        if role_id:
            tasks = [t for t in tasks if t.role_id == role_id]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    async def send_task(self, role_id: str, message: str) -> TeamTask:
        """向指定角色发送任务，通过 OpenClaw sessions API 调用对应 agent"""
        role = self._roles.get(role_id)
        if not role:
            raise ValueError(f"角色 {role_id} 不存在")

        task = TeamTask(role_id=role_id, message=message, status="running")
        self._tasks[task.id] = task
        self._save()

        try:
            # 构造发给 agent 的完整 prompt
            full_prompt = message
            if role.system_prompt:
                full_prompt = f"[系统提示: {role.system_prompt}]\n\n{message}"

            result = await self._call_agent(role.agent_id, full_prompt)
            task.result = result
            task.status = "done"
        except Exception as e:
            task.result = f"Error: {e}"
            task.status = "failed"

        self._tasks[task.id] = task
        self._save()
        return task

    async def _call_agent(self, agent_id: str, message: str) -> str:
        """调用 OpenClaw sessions_spawn API（子 agent）"""
        async with httpx.AsyncClient(timeout=120) as client:
            # 启动一个 isolated subagent run
            payload = {
                "agentId": agent_id,
                "task": message,
                "mode": "run",
                "runtime": "subagent"
            }
            resp = await client.post(
                f"{OPENCLAW_API}/api/sessions/spawn",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()

            session_key = data.get("sessionKey") or data.get("id")
            if not session_key:
                return data.get("result", str(data))

            # 轮询等待结果
            for _ in range(60):
                await asyncio.sleep(2)
                poll = await client.get(
                    f"{OPENCLAW_API}/api/sessions/{session_key}"
                )
                poll.raise_for_status()
                info = poll.json()
                status = info.get("status")
                if status in ("done", "completed", "finished"):
                    return info.get("lastMessage", {}).get("content", str(info))
                if status in ("error", "failed"):
                    return f"Agent 返回错误: {info}"

            return "任务超时（120s）"
