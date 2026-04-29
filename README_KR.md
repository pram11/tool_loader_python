# tool-loader-python

SQLite 기반 도구 메타데이터 관리 및 LangChain 에이전트용 비동기 도구 로더 라이브러리.

## 설치

```bash
pip install -e .
```

## 빠른 시작

```bash
# 1. Fernet 암호화 키 생성 (최초 1회)
python -m tool_loader keygen

# 2. 환경변수 설정
export TOOL_LOADER_FERNET_KEY=<위에서 생성한 키>
export TOOL_LOADER_DB_URL=sqlite+aiosqlite:///tools.db   # 기본값이므로 생략 가능

# 3. 도구 등록 및 목록 확인
python -m tool_loader add --name my_calc --type python --path "math:gcd" --description "GCD 계산"
python -m tool_loader list

# 4. 도구 로드 및 결과 확인
python -m tool_loader load --allowed-modules math
```

## 아키텍처 개요

```
CryptoManager → Registry (SQLite) → UniversalLoader → LangChain Tools
                                  ↗
                   ProcessManager (MCP 서브프로세스)
```

| 컴포넌트 | 역할 |
|---|---|
| `CryptoManager` | Fernet 대칭키로 env_vars 암복호화 |
| `Registry` | SQLAlchemy + aiosqlite 기반 도구 CRUD |
| `ProcessManager` | MCP 서버 서브프로세스 생명주기 관리 |
| `UniversalLoader` | MCP / Python 타입 도구를 LangChain 형식으로 로드 |
| `config_server` | 런타임 도구 관리용 내장 FastMCP 서버 |

---

## CLI 사용법

`python -m tool_loader <subcommand>` 형식으로 실행합니다.  
모든 서브커맨드는 `--db-url`과 `--fernet-key` 전역 옵션을 공유하며, 환경변수로 대체할 수 있습니다.

```
python -m tool_loader [-h] [--db-url URL] [--fernet-key KEY] SUBCOMMAND
```

| 서브커맨드 | 설명 | 주요 옵션 |
|---|---|---|
| `keygen` | Fernet 키 생성 후 stdout 출력 | — |
| `list` | 등록된 도구 목록 출력 | `--enabled-only` |
| `add` | 도구 등록 | `--name`, `--type`, `--path`, `--args`, `--env`, `--policy`, `--description` |
| `delete` | 도구 삭제 | `TOOL_ID` |
| `toggle` | 도구 활성화/비활성화 | `TOOL_ID`, `--enable` \| `--disable` |
| `load` | 활성 도구 전체 로드 후 결과 출력 | `--allowed-modules`, `--seed-builtins` |
| `serve` | config MCP 서버를 stdio 전송으로 실행 | (fernet-key 필수) |

```bash
# 키 생성
python -m tool_loader keygen

# MCP 도구 등록
python -m tool_loader add \
  --name filesystem_mcp \
  --type mcp \
  --path npx \
  --args '["-y","@modelcontextprotocol/server-filesystem","/tmp"]' \
  --policy PERSISTENT

# 도구 목록 조회 (활성만)
python -m tool_loader list --enabled-only

# 도구 비활성화 / 활성화
python -m tool_loader toggle 3 --disable
python -m tool_loader toggle 3 --enable

# 도구 삭제
python -m tool_loader delete 3

# config MCP 서버 실행
python -m tool_loader serve
```

---

## 내장 도구 (Built-in Tools)

`tool_loader.builtin_tools` 패키지에 포함된 9개의 기본 도구입니다.  
`seed_builtin_tools(registry)`를 호출하면 모두 자동 등록됩니다.

### 파일 도구 (`file_tools`)

| 도구 | 확인 필요 | 설명 |
|---|:---:|---|
| `search_files(pattern, directory=".")` | ❌ | 글로브 패턴으로 파일 검색 |
| `list_directory(directory=".", show_hidden=False)` | ❌ | 디렉토리 내용 조회 (이름, 타입, 크기) |
| `read_file(file_path)` | ❌ | 파일 텍스트 내용 읽기 |
| `write_file(file_path, content)` | ✅ | 파일 생성 또는 덮어쓰기 |
| `delete_file(file_path)` | ✅ | 파일 삭제 |

### 쉘 도구 (`shell_tools`)

| 도구 | 확인 필요 | 설명 |
|---|:---:|---|
| `execute_file(file_path, args="")` | ✅ | 스크립트 파일 실행 (.py, .sh, .js 등) |
| `run_bash(command, timeout=30)` | ✅ | bash 명령어 실행 |

### HTTP 도구 (`http_tools`)

| 도구 | 확인 필요 | 설명 |
|---|:---:|---|
| `http_request(url, method="GET", headers="{}", body="", timeout=30)` | ❌ | HTTP 요청 전송 (curl 대체) |

### 시스템 도구 (`system_tools`)

| 도구 | 확인 필요 | 설명 |
|---|:---:|---|
| `get_system_info()` | ❌ | OS, CPU 코어 수, 디스크 사용량 반환 |

### 사용자 확인 메커니즘

✅ 표시된 도구는 **실행 전 사용자 확인**이 필요합니다.

```
⚠️  다음 작업을 실행하려 합니다:
  파일 삭제: /home/user/important.txt
계속하시겠습니까? [y/N]:
```

- `y` 입력 시에만 실행, 그 외 입력 시 취소 메시지 반환
- LangChain 에이전트는 취소 결과를 받아 상위 흐름에서 처리 가능
- 비대화형 환경(EOF)에서는 자동으로 취소

### 내장 도구 등록 예시

```python
from tool_loader import CryptoManager, Registry
from tool_loader.builtin_tools import BUILTIN_MODULE, seed_builtin_tools

crypto = CryptoManager(key=...)
registry = Registry(db_url="sqlite+aiosqlite:///tools.db", crypto=crypto)
await registry.init_db()

# 미등록 도구만 자동으로 삽입 (멱등성 보장)
inserted = await seed_builtin_tools(registry)

# UniversalLoader에 모듈 허용 목록 추가
loader = UniversalLoader(
    registry=registry,
    process_manager=process_manager,
    allowed_modules={BUILTIN_MODULE},
)
```

---

## 커스텀 Python 도구 추가

```python
# 1. LangChain @tool 함수 작성
from langchain_core.tools import tool

@tool
def my_tool(x: int) -> str:
    """내 커스텀 도구."""
    return str(x * 2)

# 2. 레지스트리에 등록
from tool_loader.models import ToolSchema, ToolType

await registry.add_tool(ToolSchema(
    name="my_tool",
    type=ToolType.PYTHON,
    path_or_cmd="my_module:my_tool",  # "모듈:함수명" 형식
    description="입력값을 두 배로 반환합니다.",
))

# 3. allowed_modules에 모듈 추가
loader = UniversalLoader(
    ...,
    allowed_modules={"my_module"},
)
```

## MCP 도구 추가

```python
from tool_loader.models import ToolSchema, ToolType, TerminationPolicy

await registry.add_tool(ToolSchema(
    name="filesystem_mcp",
    type=ToolType.MCP,
    path_or_cmd="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    termination_policy=TerminationPolicy.PERSISTENT,
    description="파일시스템 MCP 서버",
))
```

## config_server (런타임 도구 관리)

내장 FastMCP 서버를 stdio 전송으로 실행하면 연결된 LLM 에이전트가 런타임에 도구를 CRUD할 수 있습니다.

```bash
# CLI로 실행 (권장)
python -m tool_loader serve

# 또는 서브패키지로 직접 실행
python -m tool_loader.config_server \
  --db-url sqlite+aiosqlite:///tools.db \
  --fernet-key <FERNET_KEY>
```

제공 MCP 도구: `list_tools`, `get_tool`, `add_tool`, `toggle_tool`, `delete_tool`

---

## 예외 처리

`tool_loader.exceptions` 에서 모든 커스텀 예외를 임포트할 수 있습니다.

| 예외 | 발생 조건 |
|---|---|
| `ToolNotFoundError` | `delete_tool(id)` 호출 시 해당 ID가 존재하지 않을 때 |
| `SystemToolError` | `is_system=True`인 도구를 수정/삭제하려 할 때 |
| `DecryptionError` | env_vars 복호화 실패 (키 불일치 등) |
| `ModuleNotAllowedError` | `allowed_modules` 화이트리스트에 없는 모듈 로드 시도 |
| `ToolLoadError` | `aload_all(safe_mode=True)` 중 개별 도구 로드 실패 |

```python
from tool_loader.exceptions import ToolNotFoundError, SystemToolError

try:
    await registry.delete_tool(tool_id)
except ToolNotFoundError:
    print("존재하지 않는 도구입니다.")
except SystemToolError:
    print("시스템 도구는 삭제할 수 없습니다.")
```

> **주의**: v0.1 이전에는 `delete_tool`이 존재하지 않는 ID를 무시했습니다.  
> 현재는 `ToolNotFoundError`를 발생시킵니다.

---

## 테스트

```bash
pytest -v --asyncio-mode=auto
```

## 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `TOOL_LOADER_FERNET_KEY` | (자동 생성) | Fernet 암호화 키 (base64) |
| `TOOL_LOADER_DB_URL` | `sqlite+aiosqlite:///tools.db` | SQLAlchemy DB URL |
