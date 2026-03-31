"""
AI Team Platform - 核心数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid


class AgentRole(BaseModel):
    """团队角色（对应一个 OpenClaw Agent）"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    agent_id: str = "main"
    description: str = ""
    system_prompt: str = ""
    is_controller: bool = False        # 是否为主控角色
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True
    session_key: Optional[str] = None  # 持久化 session key（spawn 后保留）

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SubTaskResult(BaseModel):
    """子任务执行结果"""
    role_id: str
    role_name: str
    sub_task: str                      # 主控拆解出的子任务描述
    status: str = "pending"            # pending/running/done/failed
    result: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TeamTask(BaseModel):
    """任务记录（支持普通任务和主控编排任务）"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role_id: str                       # 接收任务的角色 id（主控 or 普通）
    message: str                       # 原始任务描述
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "pending"            # pending/running/done/failed
    result: Optional[str] = None
    # 主控编排专用字段
    is_orchestrated: bool = False      # 是否为主控编排任务
    sub_tasks: List[SubTaskResult] = Field(default_factory=list)
    orchestration_plan: Optional[str] = None  # 主控的拆解方案
    # 代码生成结果
    generated_path: Optional[str] = None      # 生成的项目路径
    generated_files: List[str] = Field(default_factory=list)  # 生成的文件列表

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CreateRoleRequest(BaseModel):
    name: str
    agent_id: str = "main"
    description: str = ""
    system_prompt: str = ""
    is_controller: bool = False


class SendTaskRequest(BaseModel):
    message: str


class OrchestrationRequest(BaseModel):
    """主控任务请求"""
    controller_id: str                 # 主控角色 id
    message: str                       # 总任务
    target_role_ids: Optional[List[str]] = None  # 指定下发给哪些角色（空=自动选）
    generate_code: bool = False        # 是否在编排完成后生成代码/文件
