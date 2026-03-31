# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [v1.0.0] - 2026-03-31

### Added
- Multi-role team management (PM, Architect, Backend, Frontend, QA, DevOps, Review, Controller)
- Controller-driven orchestration: auto-decomposes tasks and dispatches to each role
- Persistent agent sessions with automatic fallback to subagent spawn on expiry
- Real-time SSE progress streaming with per-role execution timers and elapsed time display
- Async orchestration: `POST /orchestrate` returns `task_id` immediately, runs in background
- 3D Command Center visualization (Three.js) with agent state and communication links
- Role card detail drawer showing full execution output with Markdown rendering
- Direct task assignment to individual roles (bypassing controller)
- Task history with per-role sub-task result viewer
- English README (`README.md`) and Chinese README (`README.zh.md`)
- MIT License
- `.gitignore` covering `__pycache__`, `data/`, `.env` files
- GitHub Actions: CI (lint + import check + startup health check)
- GitHub Actions: Auto Release on tag push with generated changelog
- GitHub Actions: Dependency Review (pip-audit + pinned version check)
- Branch protection on `main` (require PR + CI pass + 1 review)
- `CONTRIBUTING.md` with branch strategy, commit conventions, code style, and release workflow
- Issue templates: Bug Report and Feature Request
- PR template with self-review checklist
- `SECURITY.md` with vulnerability reporting policy

### Fixed
- Concurrent subagent file lock conflicts — switched to serial execution with 3s gap
- Poll deadlock bug — replaced `user_msg count` check with content-stability detection
- Persistent session timeout hang — reduced timeout to 35s, auto-cleanup on failure
- CI startup failure: `roles.json` initialized as `{}` (dict) not `[]` (list)

---

## [v0.1.0] - 2026-03-30

### Added
- Initial project scaffold: FastAPI backend + Vanilla JS frontend
- Basic role CRUD and task orchestration prototype
- SSE event stream for real-time progress
- Visualization of orchestration progress in role cards

[Unreleased]: https://github.com/teng00123/ai_team_platform/compare/v1.0.0...HEAD
[v1.0.0]: https://github.com/teng00123/ai_team_platform/compare/v0.1.0...v1.0.0
[v0.1.0]: https://github.com/teng00123/ai_team_platform/releases/tag/v0.1.0
