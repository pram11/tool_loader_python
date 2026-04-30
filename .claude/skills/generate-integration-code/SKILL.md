# Skill: Generate Integration Code

이 스킬은 사용자가 "메인 프로젝트와 연동하는 예제 코드를 작성해줘"라고 요청할 때 사용됩니다.

## 📝 실행 지침 (Instructions)
아래의 구조와 보안 요구사항을 충족하는 `main.py` 템플릿을 생성하세요.

1. **보안 검증 콜백 포함**: `is_system`이 아닌 도구의 `TOGGLE_TOOL` 이벤트를 가로채어 CLI에서 사용자 입력(y/n)을 받는 `security_validator` 비동기 함수를 구현할 것.
2. **초기화 순서 준수**: 
   - `CryptoManager` (환경변수에서 키 로드)
   - `ProcessManager` (idle_timeout 300 설정)
   - `UniversalLoader` (위 매니저들과 화이트리스트 주입)
3. **오류 피드백 지원**: `aload_all(safe_mode=True, return_failures=True)`를 호출하여 성공과 실패를 분리하여 콘솔에 출력할 것.
4. **안전한 종료**: `finally` 블록에서 반드시 `await process_manager.close_all()`을 호출하여 잔여 프로세스를 정리할 것.

## 🎯 목표 결과물
위 지침이 모두 반영된 실행 가능한 비동기 Python 스크립트.

