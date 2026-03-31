# 开发规范

本文档定义 AI Team Platform 的代码风格、分支策略、提交规范和发布流程，确保协作有序、代码可维护。

---

## 目录

- [环境准备](#环境准备)
- [分支策略](#分支策略)
- [提交规范](#提交规范)
- [代码风格](#代码风格)
- [目录结构约定](#目录结构约定)
- [API 设计规范](#api-设计规范)
- [测试规范](#测试规范)
- [发布流程](#发布流程)
- [Code Review 清单](#code-review-清单)

---

## 环境准备

```bash
# 1. 克隆仓库
git clone https://github.com/teng00123/ai_team_platform.git
cd ai_team_platform

# 2. 创建虚拟环境（推荐）
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
pip install flake8 pyright   # 开发工具

# 4. 初始化运行数据目录
mkdir -p data
echo "[]" > data/roles.json
echo "{}" > data/tasks.json

# 5. 启动开发服务（热重载）
uvicorn main:app --host 0.0.0.0 --port 8765 --reload
```

---

## 分支策略

采用简化版 Git Flow：

```
main          ← 稳定分支，只接受 PR 合并，保护分支
  └── feat/xxx     ← 新功能开发
  └── fix/xxx      ← Bug 修复
  └── chore/xxx    ← 构建/工具/文档等杂项
  └── refactor/xxx ← 重构（不改变功能）
```

**规则：**

- `main` 分支受保护，**禁止直接 push**，必须通过 PR 合入
- 每个 PR 对应一个功能/修复，保持粒度小、可回滚
- 分支命名：`类型/简短描述`，如 `feat/add-role-template`、`fix/session-timeout`
- 分支生命周期：PR 合入后及时删除

---

## 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

[可选 body]

[可选 footer]
```

### Type 类型

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `style` | 格式调整（不影响逻辑） |
| `refactor` | 重构（不新增功能，不修复 bug） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/CI/依赖/工具等杂项 |
| `revert` | 回滚提交 |

### 示例

```bash
# 好的提交
git commit -m "feat(orchestrate): 支持并发编排多个角色"
git commit -m "fix(session): 修复持久 session 超时卡死问题"
git commit -m "docs: 更新 README 快速开始章节"
git commit -m "chore: 升级 fastapi 到 0.115.0"

# 不好的提交（避免）
git commit -m "fix bug"
git commit -m "update"
git commit -m "wip"
```

**Subject 规则：**
- 不超过 72 个字符
- 动词开头，描述做了什么（不是为什么）
- 不加句号

---

## 代码风格

### Python

- **格式化工具**：[black](https://github.com/psf/black)（行宽 100）
- **Lint 工具**：flake8（只检查语法错误和未定义名，不强制 PEP8 风格）
- **类型注解**：所有公开函数/方法必须有类型注解

```python
# ✅ 好的写法
async def get_role(role_id: str) -> AgentRole | None:
    """根据 ID 获取角色，不存在返回 None。"""
    return next((r for r in roles if r.id == role_id), None)

# ❌ 避免
def get_role(role_id):
    for r in roles:
        if r.id == role_id:
            return r
```

- **异常处理**：捕获具体异常，不使用裸 `except:`
- **日志**：使用 `logging` 模块，不用 `print`（调试除外）
- **常量**：大写下划线命名，放在文件顶部
- **魔法数字**：提取为命名常量

```python
# ✅
POLL_INTERVAL_SEC = 0.5
MAX_WAIT_SEC = 35

# ❌
await asyncio.sleep(0.5)
if elapsed > 35:
```

### 前端（Vanilla JS）

- 变量/函数：`camelCase`
- 常量：`UPPER_SNAKE_CASE`
- DOM 操作：通过 `id` 或 `data-*` 属性选取，避免深层级选择器
- 异步：统一使用 `async/await`，不混用 `.then()`
- 错误处理：`fetch` 调用必须有 `try/catch` 或 `.catch()`

---

## 目录结构约定

```
ai_team_platform/
├── main.py              # 路由注册、中间件、服务启动
├── team_manager.py      # 核心业务逻辑（编排、session 管理）
├── models.py            # Pydantic 数据模型，只定义结构，不含业务逻辑
├── cli.py               # 命令行工具入口
├── static/
│   ├── index.html       # 主界面（单文件，含 CSS + JS）
│   ├── scene.html       # 3D 指挥中心
│   └── vendor/          # 第三方库（不修改）
├── data/                # 运行时数据（不提交 git）
│   ├── roles.json
│   └── tasks.json
├── docs/                # 文档资源（截图等）
├── .github/
│   └── workflows/       # CI/CD 配置
├── requirements.txt     # 生产依赖（固定版本）
├── .gitignore
├── LICENSE
├── README.md
└── CONTRIBUTING.md      # 本文件
```

**约定：**
- `main.py` 只做路由注册和中间件，**不写业务逻辑**
- 业务逻辑集中在 `team_manager.py`
- `models.py` 纯数据结构，不引用 `team_manager`
- 新增功能模块放在独立文件，在 `main.py` 中引入

---

## API 设计规范

- 路径：小写 + 连字符，`/api/v1/role-templates`
- 方法语义：`GET` 查询、`POST` 创建、`PUT` 全量更新、`PATCH` 部分更新、`DELETE` 删除
- 响应结构统一：

```json
{
  "code": 0,
  "data": { ... },
  "message": "ok"
}
```

- 错误响应：

```json
{
  "code": 400,
  "data": null,
  "message": "role_id 不存在"
}
```

- HTTP 状态码：
  - `200` 成功
  - `201` 创建成功
  - `400` 参数错误
  - `404` 资源不存在
  - `500` 服务内部错误

- SSE 事件命名：`snake_case`，如 `sub_task_started`、`orchestration_done`

---

## 测试规范

> 当前项目为快速原型阶段，以集成测试和冒烟测试为主。

**冒烟测试（每次 PR 必跑）：**

```bash
# 启动服务
python main.py &

# 检查核心端点
curl -sf http://localhost:8765/api/roles   # 返回角色列表
curl -sf http://localhost:8765/api/tasks   # 返回任务历史
```

**手动测试清单（新功能提交前自测）：**

- [ ] 新增角色 → 能正常显示在列表
- [ ] 设为主控 → 编排面板正常出现
- [ ] 下达任务 → SSE 进度正常推送
- [ ] 点击角色卡片 → 抽屉正常展示结果
- [ ] 服务重启后 → 角色和任务数据正常恢复

**未来计划：**
- 引入 `pytest` + `httpx.AsyncClient` 做接口单测
- 覆盖率目标：核心逻辑 ≥ 60%

---

## 发布流程

```
1. 确保 main 分支 CI 全绿
        │
        ▼
2. 更新 CHANGELOG（如有）
        │
        ▼
3. 打 tag（遵循语义化版本）
   git tag -a v1.x.x -m "release: vx.x.x"
   git push origin v1.x.x
        │
        ▼
4. GitHub Actions 自动触发 release.yml
   → 自动生成 changelog
   → 自动创建 GitHub Release
```

**版本号规则（[语义化版本](https://semver.org/lang/zh-CN/)）：**

| 变更类型 | 版本号变化 | 示例 |
|---------|-----------|------|
| 不兼容的 API 变更 | `MAJOR` +1 | `1.0.0 → 2.0.0` |
| 向下兼容的新功能 | `MINOR` +1 | `1.0.0 → 1.1.0` |
| 向下兼容的 Bug 修复 | `PATCH` +1 | `1.0.0 → 1.0.1` |
| 预发布版本 | 加后缀 | `1.1.0-beta.1` |

---

## Code Review 清单

PR 提交前，作者自查：

- [ ] 代码通过本地 `flake8` 检查
- [ ] 所有新函数有类型注解
- [ ] 无硬编码 Token / 密钥 / 内网地址
- [ ] 新增配置项已更新 README
- [ ] `data/` 目录下无新文件被 `git add`
- [ ] 提交信息符合 Conventional Commits 规范
- [ ] PR 描述清楚说明了改了什么、为什么改

Reviewer 关注：

- [ ] 逻辑正确性（边界条件、异常处理）
- [ ] 是否引入新的外部依赖（需说明理由）
- [ ] API 变更是否向下兼容
- [ ] 性能影响（是否有不必要的循环/阻塞调用）
