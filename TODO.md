# 📋 Project Progress & TODOs

## 🎯 Current Sprint (현재 진행 중인 작업)
> 모든 스프린트 항목 완료. 다음 스프린트 계획 필요.

## ⏳ Backlog (대기 중인 작업)
- [x] `config_server` stdio 전송 E2E 테스트 (실제 서브프로세스로 실행)
- [x] MCP 타입 도구 실제 연동 테스트 (외부 MCP 서버 스텁 활용)
- [x] `__main__.py` CLI 엔트리포인트 정리 (`argparse` 기반 서브커맨드)
- [x] PyPI 배포용 `pyproject.toml` 정비 (메타데이터 완성, classifiers 등)

## ✅ Completed (완료된 작업)
- [x] 초기 프로젝트 명세 및 아키텍처 설계
- [x] Claude Code 전용 지침서(`CLAUDE.md`, `rules`, `skills`) 환경 구성
- [x] Pydantic 기반 도구 데이터 스키마(`ToolSchema`) 정의
- [x] `tool_loader` 패키지 디렉토리 구조 생성
- [x] `exceptions.py` 커스텀 예외 계층 구현
- [x] `CryptoManager` (Fernet 암복호화) 구현 + 테스트 4개
- [x] `Registry` (SQLAlchemy + aiosqlite CRUD, system tool 보호) 구현 + 테스트 5개
- [x] `ProcessManager` (ON_DEMAND 캐싱, idle_timeout, 데드락 방지) 구현 + 테스트 8개
- [x] `UniversalLoader` (MCP/Python 분기, 화이트리스트, safe_mode) 구현 + 테스트 5개
- [x] `config_server` (내장 FastMCP 서버, 5개 CRUD 도구) 구현 + 테스트 10개
- [x] `test_integration.py` (Registry ↔ UniversalLoader 전 경로 통합 테스트 10개)
- [x] `main.py` 연동 스크립트 (CryptoManager → Registry → ProcessManager → UniversalLoader 순서)
- [x] `pyproject.toml` 패키지 메타데이터 작성
- [x] **전체 42개 테스트 통과** (`pytest -v --asyncio-mode=auto`)
- [x] `ToolNotFoundError` 추가 및 `delete_tool` 없는 ID 처리 수정
- [x] `config_server` FastMCP API 변경 대응 (`run_async` → `run_stdio_async`)
- [x] `test_config_server_e2e.py` — 실제 stdio MCP 프로토콜 E2E 테스트 8개 추가 (**총 50개 통과**)
- [x] `tool_loader/__main__.py` — argparse 기반 CLI (keygen/list/add/delete/toggle/load/serve 7개 서브커맨드)
- [x] `pyproject.toml` 정비 — classifiers, scripts, authors, urls, mcp 의존성 추가
- [x] `_load_mcp` 버그 수정 — `"transport": "stdio"` 키 누락 및 `await client.get_tools()` 누락 수정
- [x] `testsxit/stub_mcp_server.py` — FastMCP 기반 테스트용 스텁 서버 (add_numbers, greet 2개 도구)
- [x] `test_mcp_integration.py` — 실제 stdio MCP 프로토콜 연동 테스트 8개 추가 (**총 58개 통과**)
- [x] `builtin_tools` 패키지 구현 — 9개 내장 도구 (파일 CRUD, 파일 검색, 디렉토리 조회, HTTP, 파일/bash 실행, 시스템 정보)
  - `_confirmation.py`: 위험 도구(write/delete/execute/bash) 실행 전 stdin y/N 확인 데코레이터
  - `file_tools.py`: search_files, list_directory, read_file, write_file(✅확인), delete_file(✅확인)
  - `shell_tools.py`: execute_file(✅확인), run_bash(✅확인) — 확장자 기반 인터프리터 자동 선택
  - `http_tools.py`: http_request — urllib 표준 라이브러리 기반 curl 대체
  - `system_tools.py`: get_system_info — OS/CPU/디스크 정보 반환
  - `seed_builtin_tools(registry)`: 멱등성 보장 자동 등록 헬퍼
- [x] `main.py` 업데이트 — BUILTIN_MODULE whitelist 추가, seed_builtin_tools 호출
- [x] `README.md` 작성 — 내장 도구 목록, 확인 메커니즘, 사용법 포함

## 📝 Lab Notes & Learnings (기록 및 메모)
- *2026-04-30: SQLite 비동기 처리를 위해 `aiosqlite` 드라이버를 SQLAlchemy와 결합.*
- *2026-04-30: 시스템 환경이 PEP 668(externally managed) 제약. `--break-system-packages` 또는 venv 사용 필요.*
- *2026-04-30: `pyproject.toml` build-backend는 `setuptools.build_meta`를 써야 함 (`setuptools.backends.legacy`는 구버전에서 import 불가).*
- *2026-04-30: `config_server` FastMCP 도구 직접 호출 시 `server._tool_manager._tools[name].fn`으로 접근 (내부 API, 버전 변경 주의).*
