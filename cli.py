"""
AI Team Platform - CLI 工具（可选）
快速通过命令行管理团队角色和发送任务
"""
import typer
import asyncio
from rich.console import Console
from rich.table import Table
from rich import box

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from models import CreateRoleRequest, SendTaskRequest
from team_manager import TeamManager

app = typer.Typer(help="AI Team Platform CLI")
console = Console()
manager = TeamManager()


@app.command("list")
def list_roles():
    """列出所有团队角色"""
    roles = manager.list_roles()
    if not roles:
        console.print("[yellow]暂无团队角色[/yellow]")
        return
    t = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    t.add_column("ID", style="dim", max_width=12)
    t.add_column("角色名称", style="bold")
    t.add_column("Agent ID")
    t.add_column("描述")
    for r in roles:
        t.add_row(r.id[:8] + "…", r.name, r.agent_id, r.description or "-")
    console.print(t)


@app.command("add")
def add_role(
    name: str = typer.Argument(..., help="角色名称"),
    agent_id: str = typer.Option("main", "--agent", help="OpenClaw Agent ID"),
    description: str = typer.Option("", "--desc", help="角色描述"),
    system_prompt: str = typer.Option("", "--prompt", help="系统提示词"),
):
    """新增团队角色"""
    req = CreateRoleRequest(name=name, agent_id=agent_id,
                            description=description, system_prompt=system_prompt)
    role = manager.add_role(req)
    console.print(f"[green]✅ 角色已创建[/green]: [bold]{role.name}[/bold] (id: {role.id[:8]}…)")


@app.command("delete")
def delete_role(role_id: str = typer.Argument(..., help="角色 ID（前缀匹配）")):
    """删除团队角色"""
    roles = manager.list_roles()
    matched = [r for r in roles if r.id.startswith(role_id)]
    if not matched:
        console.print(f"[red]未找到角色: {role_id}[/red]")
        raise typer.Exit(1)
    role = matched[0]
    if typer.confirm(f"确认删除角色 {role.name}？"):
        manager.delete_role(role.id)
        console.print(f"[green]✅ 角色 {role.name} 已删除[/green]")


@app.command("task")
def send_task(
    role_id: str = typer.Argument(..., help="角色 ID（前缀匹配）"),
    message: str = typer.Argument(..., help="任务内容"),
):
    """向指定角色发送任务"""
    roles = manager.list_roles()
    matched = [r for r in roles if r.id.startswith(role_id) or r.name == role_id]
    if not matched:
        console.print(f"[red]未找到角色: {role_id}[/red]")
        raise typer.Exit(1)
    role = matched[0]
    console.print(f"[cyan]📤 发送任务给 {role.name}…[/cyan]")
    task = asyncio.run(manager.send_task(role.id, message))
    status_color = "green" if task.status == "done" else "red"
    console.print(f"[{status_color}]状态: {task.status}[/{status_color}]")
    if task.result:
        console.print(f"\n[bold]结果:[/bold]\n{task.result}")


if __name__ == "__main__":
    app()
