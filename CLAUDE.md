# tool-loader-python

## ⚡ Quick Facts
- **Description**: SQLite 기반 도구 메타데이터 관리 및 LangChain 에이전트용 비동기 도구 로더 라이브러리
- **Tech Stack**: Python 3.9+, `asyncio`, `langchain-core`, `langchain-mcp-adapters`, `sqlalchemy`, `pydantic`, `cryptography`
- **Build/Install**: `pip install -e .`
- **Test Command**: `pytest -v --asyncio-mode=auto`

## 🔄 Workflow & Progress Tracking (중요)
- **상태 관리**: 프로젝트의 모든 작업 목록과 진행 상황, 실패한 접근법 등은 반드시 `TODO.md` 파일에서 관리한다.
- **세션 시작 시**: 새로운 작업을 지시받으면 가장 먼저 `TODO.md`를 읽고 현재 진행 상태(In Progress)와 다음 할 일(To Do)을 파악하라.
- **작업 완료 시**: 유의미한 코드 구현이나 버그 수정을 마쳤을 경우, 다음 순서를 반드시 따른다:
  1. `TODO.md` 업데이트 (체크박스 표시 및 노트 추가)
  2. 변경사항이 엔드유저 API/동작에 영향을 미치는지 검토
  3. 영향이 있으면 `README.md` 반영 (동작 변경 시 마이그레이션 노트 포함)
  4. `git commit` 후 `git push origin main`
- **작업 원칙**: 항상 `탐색(Explore) -> 계획(Plan) -> 코드 작성(Code) -> 검증(Verify)`의 4단계 순서로 접근한다. 코드를 짜기 전에 구조를 먼저 고민할 것.

## 📁 Key Directories
- `tool_loader/registry/`: SQLite DB 인터페이스 및 CRUD 담당
- `tool_loader/core/`: 비동기 로더, 객체 바인딩 및 프로세스 생명주기 관리
- `tool_loader/models/`: Pydantic 기반 도구 데이터 스키마
- `tool_loader/security/`: 대칭키(Fernet) 기반 환경변수 암복호화
- `tool_loader/config_server/`: 자체 관리용 내장 MCP 서버
- `tests/`: 비동기 모의(Mock) 테스트 및 DB 통합 테스트

## 🎨 Code Style & Conventions
- **Async-First**: DB 조회, 서브프로세스 관리 등 모든 I/O 작업은 반드시 `asyncio` 기반으로 작성한다.
- **Type Hinting**: 모든 함수와 클래스 시그니처에 엄격한 타입 힌팅을 적용하며, 데이터 검증은 Pydantic 모델을 통한다.
- **Error Handling**: 프로세스 데드락, DB 락, 복호화 실패 등 엣지 케이스 발생 시 명시적인 커스텀 예외(Custom Exception)를 발생시킨다.

## 🔗 References
- 데이터베이스 스키마 및 아키텍처 세부 사항은 `.claude/rules/architecture.md` 참조
