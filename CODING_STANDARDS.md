# Atlas Trading 코딩 표준

이 문서는 Atlas Trading 프로젝트의 모든 코드에 적용되는 **철칙**입니다.

## 🔴 철칙 (MUST)

### 1. FastAPI Response 타입

**규칙**: FastAPI의 response에는 **frozen dataclass만** 사용합니다.

```python
# ✅ GOOD
from dataclasses import dataclass

@dataclass(frozen=True)
class UserResponse:
    id: int
    name: str
    email: str | None

# ❌ BAD - Pydantic 사용 금지
from pydantic import BaseModel

class UserResponse(BaseModel):
    id: int
    name: str
```

**세부 사항**:
- Request에는 Pydantic 사용 가능
- Response dataclass에 메서드 추가 금지
- 오직 데이터만 담는 불변 객체로 사용

---

### 2. 타입 힌팅

**규칙**: Python 내장 타입을 사용하고, `typing` 모듈 최대한 자제합니다.

```python
# ✅ GOOD - Python 3.10+ 내장 타입
def get_user(user_id: int) -> dict[str, str] | None:
    pass

def process_items(items: list[str]) -> tuple[int, str]:
    pass

# ❌ BAD - typing 모듈 사용
from typing import Optional, Dict, List, Tuple

def get_user(user_id: int) -> Optional[Dict[str, str]]:
    pass

def process_items(items: List[str]) -> Tuple[int, str]:
    pass
```

**매핑 표**:
| typing 모듈 | 내장 타입 |
|------------|----------|
| `Optional[T]` | `T \| None` |
| `Dict[K, V]` | `dict[K, V]` |
| `List[T]` | `list[T]` |
| `Tuple[T, ...]` | `tuple[T, ...]` |
| `Set[T]` | `set[T]` |

**예외**: `typing.Generator`, `typing.Callable` 등 내장으로 표현 불가능한 경우만 허용

---

### 3. 절대경로 사용

**규칙**: 상대경로 대신 **절대경로**를 사용합니다.

```python
# ✅ GOOD
from pathlib import Path

CORE_PLATFORM_PATH = Path("/Users/jang-yeonghwan/atlas-trading/atlas-trading/core-platform")
ENV_PATH = Path("/Users/jang-yeonghwan/atlas-trading/atlas-trading/core-platform/.env")

# ❌ BAD - 상대경로 사용
env_path = Path(__file__).parent.parent / ".env"
```

**적용 범위**:
- 파일 시스템 경로
- 모듈 import 경로 (sys.path 조작 시)
- 환경 변수 파일 로딩

---

## 📘 권장 사항 (SHOULD)

### Python 버전

- **최소 버전**: Python 3.12
- 최신 언어 기능 적극 활용

### 코드 스타일

- **Formatter**: Black (line-length=100)
- **Linter**: Ruff
- **Type Checker**: mypy

### 명명 규칙

- **변수/함수**: `snake_case`
- **클래스**: `PascalCase`
- **상수**: `UPPER_SNAKE_CASE`
- **private**: `_leading_underscore`

---

## 📁 프로젝트 구조

```
atlas-trading/
├── core-platform/       # 백테스팅 엔진
├── api-server/          # FastAPI 백엔드
├── web-dashboard/       # React 프론트엔드
├── cluster-config/      # k8s 설정 (추후)
└── CODING_STANDARDS.md  # 이 문서
```

---

## 🔄 업데이트 기록

- 2026-02-15: 초기 작성
  - FastAPI response dataclass 규칙
  - 타입 힌팅 내장 타입 사용
  - 절대경로 사용 규칙
