# Architecture & Database Rules

이 파일은 `tool_loader` 모듈의 핵심 아키텍처와 DB 스키마 구조를 정의합니다. DB 계층이나 Core 로직 수정 시 이 규칙을 엄격히 따르세요.

## 🗄 Database Schema (`tools` 테이블)
SQLite 기반이며, 보안과 생명주기 관리를 위해 다음 스키마를 유지합니다.

| 컬럼명 | 타입 | 설명 | 예시 |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER (PK) | 고유 식별자 | `1` |
| `name` | TEXT | 도구 고유 명칭 | `calculator_tool` |
| `type` | TEXT | 도구 유형 | `mcp`, `python` |
| `path_or_cmd` | TEXT | 실행 경로 | `npx`, `src.math:add` |
| `args` | TEXT (JSON) | 추가 인자 | `["-y", "@mcp/server"]` |
| `env_vars` | TEXT (JSON) | 환경 변수 (Fernet 암호화 필수) | `gAAAAABk...` |
| `is_enabled` | BOOLEAN | 활성화 여부 | `1` |
| `is_system` | BOOLEAN | 시스템 도구 여부 (조작 방지용) | `0` |
| `termination_policy` | TEXT | 프로세스 종료 정책 | `PERSISTENT`, `ON_DEMAND` |
| `description` | TEXT | 도구 설명 | `사칙연산을 수행합니다.` |

## 🛠 Core Module API Specs
1. **`Registry`**: 
   - `add_tool(tool_data: ToolSchema)`: 저장 시 `env_vars` 자동 암호화
   - `get_enabled_tools() -> List[ToolSchema]`: 조회 시 `env_vars` 자동 복호화
   - `toggle_tool(tool_id, status)`: `is_system=True`일 경우 변경 거부
2. **`UniversalLoader`**:
   - `async aload_all()`: 성공/실패 내역을 분리하여 반환 (LLM 피드백용)
   - 파이썬 모듈 로드 시 주입받은 `allowed_modules` 화이트리스트 기반 검증 필수
3. **`ProcessManager`**:
   - **ON_DEMAND 캐싱**: `idle_timeout` 도입, 즉시 종료 대신 유휴 대기로 Cold Start 방지
   - **데드락 방지**: 백그라운드 태스크로 `stdout`/`stderr` 스트림 지속적 비동기 읽기

