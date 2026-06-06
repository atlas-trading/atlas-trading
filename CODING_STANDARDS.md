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

### 3. Dataclass 규칙

**규칙**: 모든 dataclass는 `frozen=True, kw_only=True`로 선언합니다.

```python
# ✅ GOOD
@dataclass(frozen=True, kw_only=True)
class Order:
    id: str
    quantity: Decimal

# 변경이 필요한 경우 replace() 사용
new_order = dataclasses.replace(order, quantity=Decimal("0.5"))

# ❌ BAD - mutable dataclass
@dataclass
class Order:
    id: str
    quantity: Decimal
```

---

## 📘 권장 사항 (SHOULD)

### Python 버전

- **최소 버전**: Python 3.12
- 최신 언어 기능 적극 활용

### 패키지 관리

- **패키지 매니저**: uv (pip 직접 사용 금지)
- `uv pip install -e ".[dev]"` 로 설치

### 코드 스타일

- **Linter / Formatter**: Ruff (line-length=100)
- **Type Checker**: mypy (선택)

### 명명 규칙

- **변수/함수**: `snake_case`
- **클래스**: `PascalCase`
- **상수**: `UPPER_SNAKE_CASE`
- **private**: `_leading_underscore`

---

## 📁 프로젝트 구조

```
atlas-trading/
├── core-platform/       # 트레이딩 엔진 (Python asyncio)
├── api-server/          # FastAPI 백엔드
├── web-dashboard/       # React + Vite 프론트엔드
├── cluster-config/      # k8s / ArgoCD 설정
├── infrastructure/      # docker-compose (PostgreSQL, Prometheus 등)
└── docs/                # 설계 문서
```

---

## 🔄 업데이트 기록

- 2026-02-15: 초기 작성
- 2026-06-06: Dataclass 규칙 추가, uv 패키지 매니저 명시, 프로젝트 구조 갱신
