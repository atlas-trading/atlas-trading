"""
Strategy configuration API endpoints

전략 설정 관리를 위한 REST API
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.models.base import get_db
from app.models.strategy import StrategyConfig


router = APIRouter()


# Pydantic Schemas
class ParameterSchemaResponse(BaseModel):
    """파라미터 스키마 응답"""
    name: str
    type: str
    default: Any
    min: float = None
    max: float = None
    step: float = None
    options: List[Any] = None
    description: str
    required: bool


class StrategyInfoResponse(BaseModel):
    """전략 정보 응답"""
    strategy_name: str
    display_name: str = None
    description: str = None
    parameter_schema: List[ParameterSchemaResponse]


class StrategyConfigResponse(BaseModel):
    """전략 설정 응답"""
    id: int
    strategy_name: str
    display_name: str = None
    description: str = None
    parameters: Dict[str, Any]
    is_active: bool
    is_live: bool
    created_at: str
    updated_at: str
    last_backtest_id: int = None
    last_backtest_return: float = None
    last_backtest_sharpe: float = None
    last_backtest_date: str = None


class StrategyConfigCreate(BaseModel):
    """전략 설정 생성 요청"""
    strategy_name: str = Field(..., description="Strategy class name")
    display_name: str = Field(None, description="Display name for UI")
    description: str = Field(None, description="Strategy description")
    parameters: Dict[str, Any] = Field({}, description="Strategy parameters")
    is_active: bool = Field(True, description="Is strategy active")


class StrategyConfigUpdate(BaseModel):
    """전략 설정 업데이트 요청"""
    display_name: str = None
    description: str = None
    parameters: Dict[str, Any] = None
    is_active: bool = None
    is_live: bool = None


# Strategy registry (전략 클래스 등록)
_STRATEGY_REGISTRY = {}


def register_strategy(strategy_class):
    """전략 클래스를 레지스트리에 등록"""
    _STRATEGY_REGISTRY[strategy_class.__name__] = strategy_class
    return strategy_class


# 전략 클래스 자동 등록
def _register_all_strategies():
    """모든 전략을 레지스트리에 자동 등록"""
    try:
        from app.strategies import (
            StatisticalArbitrageStrategy,
            ICTSmartMoneyStrategy,
            MarketMicrostructureStrategy,
            AdaptiveGridTradingStrategy,
            TriangularArbitrageStrategy,
        )

        register_strategy(StatisticalArbitrageStrategy)
        register_strategy(ICTSmartMoneyStrategy)
        register_strategy(MarketMicrostructureStrategy)
        register_strategy(AdaptiveGridTradingStrategy)
        register_strategy(TriangularArbitrageStrategy)

        print(f"✓ Registered {len(_STRATEGY_REGISTRY)} strategies")
    except Exception as e:
        print(f"⚠️ Failed to register strategies: {e}")


# 서버 시작 시 전략 등록
_register_all_strategies()


def get_strategy_class(strategy_name: str):
    """전략 클래스 조회"""
    if strategy_name not in _STRATEGY_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
    return _STRATEGY_REGISTRY[strategy_name]


# API Endpoints

@router.get("/available", response_model=List[StrategyInfoResponse])
def list_available_strategies():
    """
    사용 가능한 전략 목록 조회

    Returns:
        전략 이름, 설명, 파라미터 스키마 목록
    """
    strategies = []
    for name, strategy_class in _STRATEGY_REGISTRY.items():
        # 임시 인스턴스 생성해서 메타데이터 가져오기
        try:
            temp_instance = strategy_class()
            description = temp_instance.get_description()
        except Exception as e:
            # 전략 인스턴스 생성 실패 시 클래스 docstring 사용
            description = strategy_class.__doc__.strip().split('\n')[0] if strategy_class.__doc__ else ""

        strategies.append({
            'strategy_name': name,
            'display_name': name.replace('Strategy', ''),
            'description': description,
            'parameter_schema': strategy_class.get_parameter_schema()
        })

    return strategies


@router.get("/configs", response_model=List[StrategyConfigResponse])
def list_strategy_configs(
    is_active: bool = None,
    db: Session = Depends(get_db)
):
    """
    저장된 전략 설정 목록 조회

    Args:
        is_active: 활성화 여부로 필터링 (선택)

    Returns:
        전략 설정 목록
    """
    query = db.query(StrategyConfig)

    if is_active is not None:
        query = query.filter(StrategyConfig.is_active == is_active)

    configs = query.order_by(StrategyConfig.updated_at.desc()).all()
    return [config.to_dict() for config in configs]


@router.get("/configs/{strategy_name}", response_model=StrategyConfigResponse)
def get_strategy_config(
    strategy_name: str,
    db: Session = Depends(get_db)
):
    """
    특정 전략의 설정 조회

    Args:
        strategy_name: 전략 이름

    Returns:
        전략 설정
    """
    config = db.query(StrategyConfig).filter(
        StrategyConfig.strategy_name == strategy_name
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail=f"Strategy config '{strategy_name}' not found")

    return config.to_dict()


@router.post("/configs", response_model=StrategyConfigResponse, status_code=201)
def create_strategy_config(
    config_data: StrategyConfigCreate,
    db: Session = Depends(get_db)
):
    """
    새 전략 설정 생성

    Args:
        config_data: 전략 설정 데이터

    Returns:
        생성된 전략 설정
    """
    # 전략 클래스 존재 여부 확인
    strategy_class = get_strategy_class(config_data.strategy_name)

    # 파라미터 검증
    temp_instance = strategy_class(**config_data.parameters)
    errors = temp_instance.validate_parameters(config_data.parameters)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Parameter validation failed", "errors": errors}
        )

    # 중복 확인
    existing = db.query(StrategyConfig).filter(
        StrategyConfig.strategy_name == config_data.strategy_name
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Strategy config '{config_data.strategy_name}' already exists"
        )

    # 생성
    config = StrategyConfig(
        strategy_name=config_data.strategy_name,
        display_name=config_data.display_name or config_data.strategy_name.replace('Strategy', ''),
        description=config_data.description,
        parameters=config_data.parameters,
        is_active=config_data.is_active
    )

    db.add(config)
    db.commit()
    db.refresh(config)

    return config.to_dict()


@router.put("/configs/{strategy_name}", response_model=StrategyConfigResponse)
def update_strategy_config(
    strategy_name: str,
    update_data: StrategyConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    전략 설정 업데이트

    Args:
        strategy_name: 전략 이름
        update_data: 업데이트할 데이터

    Returns:
        업데이트된 전략 설정
    """
    config = db.query(StrategyConfig).filter(
        StrategyConfig.strategy_name == strategy_name
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail=f"Strategy config '{strategy_name}' not found")

    # 파라미터 검증 (파라미터 업데이트인 경우)
    if update_data.parameters is not None:
        strategy_class = get_strategy_class(strategy_name)
        temp_instance = strategy_class(**update_data.parameters)
        errors = temp_instance.validate_parameters(update_data.parameters)
        if errors:
            raise HTTPException(
                status_code=400,
                detail={"message": "Parameter validation failed", "errors": errors}
            )

    # 업데이트
    if update_data.display_name is not None:
        config.display_name = update_data.display_name
    if update_data.description is not None:
        config.description = update_data.description
    if update_data.parameters is not None:
        config.parameters = update_data.parameters
    if update_data.is_active is not None:
        config.is_active = update_data.is_active
    if update_data.is_live is not None:
        config.is_live = update_data.is_live

    db.commit()
    db.refresh(config)

    return config.to_dict()


@router.delete("/configs/{strategy_name}", status_code=204)
def delete_strategy_config(
    strategy_name: str,
    db: Session = Depends(get_db)
):
    """
    전략 설정 삭제

    Args:
        strategy_name: 전략 이름
    """
    config = db.query(StrategyConfig).filter(
        StrategyConfig.strategy_name == strategy_name
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail=f"Strategy config '{strategy_name}' not found")

    db.delete(config)
    db.commit()

    return None


@router.post("/configs/{strategy_name}/validate")
def validate_strategy_parameters(
    strategy_name: str,
    parameters: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    전략 파라미터 검증 (저장 전 검증용)

    Args:
        strategy_name: 전략 이름
        parameters: 검증할 파라미터

    Returns:
        검증 결과 (에러가 있으면 errors, 없으면 valid=True)
    """
    strategy_class = get_strategy_class(strategy_name)
    temp_instance = strategy_class(**parameters)
    errors = temp_instance.validate_parameters(parameters)

    if errors:
        return {"valid": False, "errors": errors}
    else:
        return {"valid": True, "message": "Parameters are valid"}


@router.get("/symbols", response_model=List[str])
def list_supported_symbols():
    """
    지원되는 거래 심볼 목록 반환

    Returns:
        심볼 리스트
    """
    # 현재 지원되는 주요 심볼들
    return [
        'BTCUSDT',
        'ETHUSDT',
        'BNBUSDT',
        'SOLUSDT',
        'ADAUSDT',
        'XRPUSDT',
        'DOGEUSDT',
        'MATICUSDT',
        'DOTUSDT',
        'AVAXUSDT',
        'LINKUSDT',
        'ATOMUSDT',
        'UNIUSDT',
        'LTCUSDT',
        'NEARUSDT',
    ]
