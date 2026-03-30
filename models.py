"""
AI Team Platform - 核心数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class AgentRole(BaseModel):
    """团队角色（对应一个 OpenClaw Agent）"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                          # 角色名称，如 "产品经理"
    agent_id: str                      # OpenClaw agent id，如 "main"
    description: str = ""              # 角色职责描述
    system_prompt: str = ""            # 该角色的系统提示词
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TeamTask(BaseModel):
    """发给某个角色的任务"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role_id: str
    message: str
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "pending"            # pending / running / done / failed
    result: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CreateRoleRequest(BaseModel):
    name: str
    agent_id: str = "main"
    description: str = ""
    system_prompt: str = ""


class SendTaskRequest(BaseModel):
    message: str
