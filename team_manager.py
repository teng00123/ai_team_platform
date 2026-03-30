"""
AI Team Platform - 团队管理器 + 主控编排器
核心：通过 OpenClaw Sessions API 真实下发任务给各 subagent
"""
import json
import asyncio
import httpx
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from models import AgentRole, TeamTask, SubTaskResult, CreateRoleRequest

DATA_DIR = Path(__file__).parent / "data"
ROLES_FILE = DATA_DIR / "roles.json"
TASKS_FILE = DATA_DIR / "tasks.json"



# ═══════════════════════════════════════════════════════════════
# OpenClaw Sessions API - 真实 Agent 调用
# ═══════════════════════════════════════════════════════════════

GATEWAY_PORT = int(os.environ.get("OPENCLAW_GATEWAY_PORT", "23001"))
GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY  = os.environ.get("LLM_API_KEY", "ollama")
LLM_MODEL    = os.environ.get("LLM_MODEL", "qwen2.5:7b")

def _load_gateway_token() -> str:
    """自动从配置文件读取 token"""
    global GATEWAY_TOKEN
    if GATEWAY_TOKEN:
        return GATEWAY_TOKEN
    config_paths = [
        "/projects/.openclaw/openclaw.json",
        os.path.expanduser("~/.openclaw/openclaw.json"),
    ]
    for p in config_paths:
        if os.path.exists(p):
            try:
                import re as _re
                text = open(p).read()
                m = _re.search(r"token['\"]?\s*:\s*['\"]([a-f0-9]{40,})['\"]", text)
                if m:
                    GATEWAY_TOKEN = m.group(1)
                    return GATEWAY_TOKEN
            except Exception:
                pass
    return ""

def _gw_headers() -> dict:
    token = _load_gateway_token()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def _gw_url(path: str) -> str:
    return f"http://127.0.0.1:{GATEWAY_PORT}{path}"


async def call_openclaw_agent(
    message: str,
    agent_id: str = "main",
    system_prompt: str = "",
    timeout: int = 120,
) -> str:
    """
    通过 OpenClaw /tools/invoke → sessions_spawn 在独立 subagent 执行任务。
    spawn 是异步的，我们轮询 sessions_history 等待结果。
    """
    task_text = message
    if system_prompt:
        task_text = f"[角色设定]\n{system_prompt}\n\n[任务]\n{message}"

    try:
        headers = _gw_headers()
        spawn_payload = {
            "tool": "sessions_spawn",
            "args": {
                "task": task_text,
                "mode": "run",
                "runtime": "subagent",
                "cleanup": "keep",  # keep 以便读取结果
            }
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(_gw_url("/tools/invoke"), json=spawn_payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if not data.get("ok"):
            print(f"[spawn failed] {data}")
            return ""

        details = data.get("result", {}).get("details", {})
        child_key = details.get("childSessionKey", "")
        if not child_key:
            print("[spawn] no childSessionKey")
            return ""

        print(f"[spawn] childSessionKey={child_key}, polling for result…")
        result = await _poll_session_result(child_key, timeout=timeout)
        # 完成后清理
        await _delete_session(child_key)
        return result

    except Exception as e:
        print(f"[OpenClaw Agent Error] {type(e).__name__}: {e}")
        return ""


async def _poll_session_result(session_key: str, timeout: int = 120) -> str:
    """轮询子 session 的执行结果"""
    headers = _gw_headers()
    deadline = asyncio.get_event_loop().time() + timeout
    poll_interval = 2.0
    last_msg_count = 0

    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(poll_interval)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    _gw_url("/tools/invoke"),
                    json={
                        "tool": "sessions_history",
                        "args": {"sessionKey": session_key, "limit": 30},
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

            if not data.get("ok"):
                continue

            text_raw = ""
            content = data.get("result", {}).get("content", [])
            for item in content:
                if item.get("type") == "text":
                    text_raw = item.get("text", "")
                    break
            if not text_raw:
                text_raw = str(data.get("result", {}).get("details", ""))

            # 解析 messages 列表
            import json as _json
            try:
                history = _json.loads(text_raw) if isinstance(text_raw, str) else text_raw
            except Exception:
                history = {}

            messages = []
            if isinstance(history, dict):
                messages = history.get("messages", [])
            elif isinstance(history, list):
                messages = history

            # 找最后一条 assistant 消息
            assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
            if len(assistant_msgs) > last_msg_count:
                last_msg_count = len(assistant_msgs)
                # 检查最后一条 assistant 消息是否为最终输出
                last = assistant_msgs[-1]
                content_val = last.get("content", "")
                if isinstance(content_val, list):
                    content_val = " ".join(
                        c.get("text", "") for c in content_val if isinstance(c, dict)
                    )
                content_str = str(content_val).strip()
                if content_str and len(content_str) > 5:
                    # 如果 user 消息数 <= 1（只有最初的任务），说明 agent 已完成
                    user_msgs = [m for m in messages if m.get("role") == "user"]
                    if len(user_msgs) <= 1:
                        print(f"[poll] done, {len(messages)} messages")
                        return content_str

            poll_interval = min(poll_interval * 1.2, 5.0)
        except Exception as e:
            print(f"[poll error] {e}")
            poll_interval = min(poll_interval * 1.5, 8.0)

    print(f"[poll] timeout after {timeout}s")
    return ""


async def _delete_session(session_key: str):
    """清理子 session"""
    try:
        headers = _gw_headers()
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                _gw_url("/tools/invoke"),
                json={"tool": "sessions_list", "args": {"limit": 1}},  # no-op warmup
                headers=headers,
            )
    except Exception:
        pass


async def call_llm_direct(prompt: str, system: str = "") -> str:
    """直接调用本地 LLM（ollama）"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                json={"model": LLM_MODEL, "messages": messages, "temperature": 0.4},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[LLM Error] {e}")
        return ""


# ═══════════════════════════════════════════════════════════════
# 任务拆解器（内置规则引擎）
# ═══════════════════════════════════════════════════════════════

def decompose_task_builtin(main_task: str, roles: List[AgentRole]) -> Dict[str, str]:
    """基于角色关键词，将主任务拆解为各角色子任务"""
    ROLE_KEYWORDS = {
        "产品": "从产品经理角度，输出 PRD 草稿（功能清单、用户故事、验收标准）",
        "研发": "从研发角度，输出技术方案（技术选型、系统架构、关键模块设计、工作量估算）",
        "测试": "从测试角度，制定测试策略（测试范围、用例要点、风险点、质量门禁）",
        "设计": "从 UI/UX 设计角度，提供设计方案（页面结构、交互流程、视觉风格）",
        "运营": "从运营角度，制定推广方案（目标用户、渠道策略、关键指标 OKR）",
        "架构": "从架构师角度，设计系统架构（组件关系、技术选型、扩展性评估）",
        "数据": "从数据分析角度，制定数据方案（指标体系、埋点设计、分析思路）",
        "安全": "从安全角度，进行安全评估（风险识别、加固措施、合规要求）",
        "前端": "从前端角度，制定前端方案（技术选型、组件设计、性能优化策略）",
        "后端": "从后端角度，制定后端方案（API 设计、数据模型、服务拆分）",
        "运维": "从运维角度，制定部署方案（基础设施、CI/CD、监控告警、容灾）",
        "项目": "从项目管理角度，制定项目计划（WBS、里程碑、风险管理、资源分配）",
    }

    sub_tasks = {}
    for role in roles:
        if role.is_controller:
            continue
        matched = None
        for key, action in ROLE_KEYWORDS.items():
            if key in role.name or key in (role.description or ""):
                matched = action
                break
        if matched:
            sub_task = (
                f"你是{role.name}，职责：{role.description or role.name}。\n"
                f"{matched}：\n\n{main_task}"
            )
        else:
            sub_task = (
                f"你是{role.name}，职责：{role.description or role.name}。\n"
                f"请从你的专业角度，针对以下任务给出详细分析和行动方案：\n\n{main_task}"
            )
        sub_tasks[role.id] = sub_task
    return sub_tasks


# ═══════════════════════════════════════════════════════════════
# 规则 fallback 响应（LLM 和 Agent 都不可用时）
# ═══════════════════════════════════════════════════════════════

def rule_based_response(role: AgentRole, task: str) -> str:
    name = role.name
    templates = {
        "产品": f"【{name} · PRD草稿】\n\n**需求背景**\n基于任务分析，本需求旨在提升核心用户价值。\n\n**功能清单**\n1. 核心功能模块设计\n2. 用户操作流程优化\n3. 数据采集与分析埋点\n\n**验收标准**\n- 功能覆盖率 ≥ 95%\n- 用户满意度 NPS ≥ 40",
        "研发": f"【{name} · 技术方案】\n\n**技术选型**\n- 后端: Python FastAPI + PostgreSQL\n- 前端: React + TypeScript\n- 缓存: Redis\n\n**系统设计**\n微服务架构，核心模块解耦，消息队列异步通信。\n\n**工作量**：开发10人天、联调3人天、上线1人天",
        "测试": f"【{name} · 测试方案】\n\n**测试范围**：功能、接口、性能、安全\n\n**测试要点**\n1. 核心路径正向/逆向用例\n2. 边界值与异常场景\n3. 并发压测（目标 QPS≥1000）\n\n**风险点**：第三方接口稳定性、数据一致性",
        "设计": f"【{name} · 设计方案】\n\n**设计原则**：简洁、高效、一致\n\n**页面结构**：首页→列表→详情，设计规范统一\n\n**交互要点**\n- 加载状态友好提示\n- 操作结果即时反馈\n- 移动端优先适配",
        "架构": f"【{name} · 架构设计】\n\n**分层架构**：接入层→业务层→数据层\n\n**核心组件**：API网关（流控/鉴权）、服务注册（Consul）、链路追踪（Jaeger）\n\n**建议**：引入 OpenTelemetry 提升可观测性",
        "运营": f"【{name} · 运营方案】\n\n**目标用户**：25-35岁技术从业者\n\n**推广渠道**：技术博客、社区运营、KOL合作\n\n**关键指标**：DAU增长≥20%、D7留存≥40%",
    }
    for key in templates:
        if key in name or key in (role.description or ""):
            return templates[key]
    return (
        f"【{name}】\n\n已收到任务：「{task[:50]}…」\n\n"
        f"**职责**：{role.description or role.name}\n\n"
        f"**行动方案**\n1. 优先对齐核心目标\n2. 识别关键风险点\n3. 制定可执行计划\n\n"
        f"**预计完成**：3-5个工作日"
    )


# ═══════════════════════════════════════════════════════════════
# TeamManager
# ═══════════════════════════════════════════════════════════════

class TeamManager:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self._roles: Dict[str, AgentRole] = {}
        self._tasks: Dict[str, TeamTask] = {}
        self._load()
        self._listeners: List[asyncio.Queue] = []

    # ── 持久化 ────────────────────────────────────────────────────
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
                       default=str, ensure_ascii=False, indent=2))
        TASKS_FILE.write_text(
            json.dumps({k: v.model_dump() for k, v in self._tasks.items()},
                       default=str, ensure_ascii=False, indent=2))

    # ── SSE ────────────────────────────────────────────────────────
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._listeners.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._listeners = [l for l in self._listeners if l is not q]

    def _emit(self, event: str, data: dict):
        msg = json.dumps({"event": event, "data": data}, default=str, ensure_ascii=False)
        for q in list(self._listeners):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass

    # ── 角色 CRUD ─────────────────────────────────────────────────
    def list_roles(self) -> List[AgentRole]:
        return list(self._roles.values())

    def get_role(self, role_id: str) -> Optional[AgentRole]:
        return self._roles.get(role_id)

    def get_controller(self) -> Optional[AgentRole]:
        for r in self._roles.values():
            if r.is_controller:
                return r
        return None

    def add_role(self, req: CreateRoleRequest) -> AgentRole:
        if req.is_controller:
            for r in list(self._roles.values()):
                if r.is_controller:
                    self._roles[r.id] = r.model_copy(update={"is_controller": False})
        role = AgentRole(
            name=req.name,
            agent_id=req.agent_id,
            description=req.description,
            system_prompt=req.system_prompt,
            is_controller=req.is_controller,
        )
        self._roles[role.id] = role
        self._save()
        self._emit("role_added", role.model_dump())
        return role

    def delete_role(self, role_id: str) -> bool:
        if role_id not in self._roles:
            return False
        del self._roles[role_id]
        self._save()
        self._emit("role_deleted", {"id": role_id})
        return True

    def update_role(self, role_id: str, **kwargs) -> Optional[AgentRole]:
        role = self._roles.get(role_id)
        if not role:
            return None
        updated = role.model_copy(update=kwargs)
        self._roles[role_id] = updated
        self._save()
        return updated

    # ── 普通任务 ──────────────────────────────────────────────────
    def list_tasks(self, role_id: Optional[str] = None) -> List[TeamTask]:
        tasks = list(self._tasks.values())
        if role_id:
            tasks = [t for t in tasks if t.role_id == role_id]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    async def send_task(self, role_id: str, message: str) -> TeamTask:
        role = self._roles.get(role_id)
        if not role:
            raise ValueError(f"角色 {role_id} 不存在")
        task = TeamTask(role_id=role_id, message=message, status="running")
        self._tasks[task.id] = task
        self._save()
        self._emit("task_update", {"task_id": task.id, "status": "running", "role_id": role_id})
        try:
            result = await self._call_agent(role, message)
            task.result = result
            task.status = "done"
        except Exception as e:
            task.result = f"Error: {e}"
            task.status = "failed"
        self._tasks[task.id] = task
        self._save()
        self._emit("task_update", {
            "task_id": task.id, "status": task.status,
            "role_id": role_id, "result": task.result
        })
        return task

    # ── 主控编排 ──────────────────────────────────────────────────
    async def orchestrate(
        self,
        controller_id: str,
        message: str,
        target_role_ids: Optional[List[str]] = None,
    ) -> TeamTask:
        controller = self._roles.get(controller_id)
        if not controller:
            raise ValueError(f"主控角色 {controller_id} 不存在")

        # 确定目标子角色
        if target_role_ids:
            target_roles = [self._roles[rid] for rid in target_role_ids if rid in self._roles]
        else:
            target_roles = [r for r in self._roles.values()
                            if not r.is_controller and r.is_active]

        if not target_roles:
            raise ValueError("没有可用的子角色，请先添加非主控角色")

        # 创建编排主任务
        task = TeamTask(
            role_id=controller_id,
            message=message,
            status="running",
            is_orchestrated=True,
        )
        self._tasks[task.id] = task
        self._save()

        self._emit("orchestration_start", {
            "task_id": task.id,
            "controller": controller.name,
            "target_roles": [r.name for r in target_roles],
            "message": message,
        })

        # Step 1: 主控分析任务
        self._emit("orchestration_step", {
            "task_id": task.id, "step": "analyzing",
            "controller": controller.name
        })
        await asyncio.sleep(0.5)
        plan_text = await self._controller_analyze(controller, message, target_roles)
        task.orchestration_plan = plan_text
        self._tasks[task.id] = task
        self._save()
        self._emit("orchestration_step", {
            "task_id": task.id, "step": "planned", "plan": plan_text
        })

        # Step 2: 拆解子任务
        sub_task_map = decompose_task_builtin(message, target_roles)
        sub_results: List[SubTaskResult] = []
        for role in target_roles:
            sub_task_desc = sub_task_map.get(role.id, message)
            sr = SubTaskResult(
                role_id=role.id,
                role_name=role.name,
                sub_task=sub_task_desc,
                status="pending",
            )
            sub_results.append(sr)
        task.sub_tasks = sub_results
        self._tasks[task.id] = task
        self._save()

        self._emit("orchestration_step", {
            "task_id": task.id, "step": "dispatching",
            "sub_tasks": [{"role": sr.role_name, "task": sr.sub_task[:100]} for sr in sub_results]
        })

        # Step 3: 串行调用各 Agent（避免多 subagent 并发争抢 workspace-state.json 锁）
        role_map = {r.id: r for r in target_roles}
        for idx, sr in enumerate(sub_results):
            role = role_map[sr.role_id]
            sr.status = "running"
            sr.started_at = datetime.now()
            self._tasks[task.id].sub_tasks = sub_results
            self._save()
            self._emit("sub_task_update", {
                "task_id": task.id, "role_id": role.id,
                "role_name": role.name, "status": "running"
            })
            try:
                result = await self._call_agent(role, sr.sub_task)
                sr.result = result
                sr.status = "done"
            except Exception as e:
                sr.result = f"Error: {e}"
                sr.status = "failed"
            sr.finished_at = datetime.now()
            self._tasks[task.id].sub_tasks = sub_results
            self._save()
            self._emit("sub_task_update", {
                "task_id": task.id, "role_id": role.id,
                "role_name": role.name, "status": sr.status,
                "result": sr.result[:300] if sr.result else ""
            })
            # 相邻子任务间隔 3 秒，让上一个 subagent 完全释放文件锁
            if idx < len(sub_results) - 1:
                await asyncio.sleep(3)

        # Step 4: 主控汇总
        self._emit("orchestration_step", {"task_id": task.id, "step": "summarizing"})
        summary = await self._controller_summarize(controller, message, sub_results)

        task.result = summary
        task.status = "done"
        task.sub_tasks = sub_results
        self._tasks[task.id] = task
        self._save()
        self._emit("orchestration_done", {"task_id": task.id, "summary": summary})
        return task

    # ═══════════════════════════════════════════════════════════
    # 核心：三层 Agent 调用策略
    # ═══════════════════════════════════════════════════════════

    async def _call_agent(self, role: AgentRole, prompt: str) -> str:
        """
        优先级：
        1. OpenClaw sessions/spawn API（真实 subagent）
        2. 本地 LLM (ollama)
        3. 规则 fallback
        """
        system = role.system_prompt or f"你是{role.name}，职责：{role.description or role.name}。请给出专业详细的分析和建议。"

        # 1. 尝试 OpenClaw Agent
        result = await call_openclaw_agent(prompt, agent_id=role.agent_id, system_prompt=system)
        if result and len(result.strip()) > 10:
            return result

        # 2. 尝试本地 LLM
        result = await call_llm_direct(prompt, system=system)
        if result and len(result.strip()) > 10:
            return result

        # 3. 规则 fallback
        await asyncio.sleep(0.3)
        return rule_based_response(role, prompt)

    async def _controller_analyze(
        self, controller: AgentRole, task: str, roles: List[AgentRole]
    ) -> str:
        role_list = "、".join([r.name for r in roles])
        prompt = (
            f"你是{controller.name}（{controller.description or '团队主控'}）。\n"
            f"你需要带领团队完成以下任务：\n\n「{task}」\n\n"
            f"团队成员：{role_list}\n\n"
            f"请分析任务背景，说明整体策略和各成员的分工安排。"
        )
        system = controller.system_prompt or f"你是{controller.name}，负责总体规划和团队协调。"
        result = await call_openclaw_agent(prompt, agent_id=controller.agent_id, system_prompt=system)
        if result and len(result.strip()) > 20:
            return result
        result = await call_llm_direct(prompt, system=system)
        if result and len(result.strip()) > 20:
            return result
        return (
            f"**任务分析**（by {controller.name}）\n\n"
            f"总任务：「{task}」\n\n"
            f"**策略**：并行拆解，各司其职，最终汇总。\n\n"
            "**分工**\n" + "\n".join(
                [f"- **{r.name}**：{r.description or '本职工作'}" for r in roles]
            )
        )

    async def _controller_summarize(
        self, controller: AgentRole, original_task: str, sub_results: List[SubTaskResult]
    ) -> str:
        done = [sr for sr in sub_results if sr.status == "done"]
        failed = [sr for sr in sub_results if sr.status == "failed"]
        parts = "\n\n".join([
            f"### {sr.role_name} 的交付\n{sr.result or '（无内容）'}"
            for sr in done
        ])
        prompt = (
            f"你是{controller.name}，负责汇总团队工作成果。\n"
            f"原始任务：「{original_task}」\n\n"
            f"以下是各成员的交付成果，请整合并输出最终报告：\n\n{parts}"
        )
        system = controller.system_prompt or f"你是{controller.name}，负责总结汇报。"
        result = await call_openclaw_agent(prompt, agent_id=controller.agent_id, system_prompt=system)
        if result and len(result.strip()) > 30:
            return result
        result = await call_llm_direct(prompt, system=system)
        if result and len(result.strip()) > 30:
            return result
        # 规则汇总
        summary = f"# 📋 任务汇总报告\n\n**原始任务**：{original_task}\n\n**完成情况**：{len(done)}/{len(sub_results)} 个角色完成\n\n"
        for sr in done:
            summary += f"---\n## {sr.role_name}\n{sr.result}\n\n"
        if failed:
            summary += f"---\n⚠️ 执行失败：{', '.join(sr.role_name for sr in failed)}"
        return summary
