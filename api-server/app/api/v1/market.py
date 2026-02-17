"""Market data API endpoints"""
from typing import List
from fastapi import APIRouter

router = APIRouter()


@router.get("/symbols", response_model=List[dict])
def get_available_symbols():
    """
    사용 가능한 거래 심볼 목록 조회

    Returns:
        심볼 목록 (심볼명, 이름, 설명)
    """
    symbols = [
        {
            'symbol': 'BTCUSDT',
            'name': 'Bitcoin',
            'description': 'Bitcoin / Tether',
            'use_case': 'Digital Gold',
            'volatility': 'medium'
        },
        {
            'symbol': 'ETHUSDT',
            'name': 'Ethereum',
            'description': 'Ethereum / Tether',
            'use_case': 'Smart Contracts',
            'volatility': 'medium'
        },
        {
            'symbol': 'BNBUSDT',
            'name': 'Binance Coin',
            'description': 'Binance Coin / Tether',
            'use_case': 'Exchange Token',
            'volatility': 'medium'
        },
        {
            'symbol': 'SOLUSDT',
            'name': 'Solana',
            'description': 'Solana / Tether',
            'use_case': 'High-Performance L1',
            'volatility': 'high'
        },
        {
            'symbol': 'ADAUSDT',
            'name': 'Cardano',
            'description': 'Cardano / Tether',
            'use_case': 'Academic Blockchain',
            'volatility': 'high'
        },
        {
            'symbol': 'XRPUSDT',
            'name': 'Ripple',
            'description': 'Ripple / Tether',
            'use_case': 'Cross-Border Payment',
            'volatility': 'high'
        },
        {
            'symbol': 'AVAXUSDT',
            'name': 'Avalanche',
            'description': 'Avalanche / Tether',
            'use_case': 'DeFi Platform',
            'volatility': 'high'
        },
        {
            'symbol': 'DOTUSDT',
            'name': 'Polkadot',
            'description': 'Polkadot / Tether',
            'use_case': 'Interchain',
            'volatility': 'high'
        },
        {
            'symbol': 'LINKUSDT',
            'name': 'Chainlink',
            'description': 'Chainlink / Tether',
            'use_case': 'Oracle Network',
            'volatility': 'high'
        },
    ]

    return symbols


@router.get("/timeframes", response_model=List[dict])
def get_available_timeframes():
    """
    사용 가능한 타임프레임 목록 조회

    Returns:
        타임프레임 목록
    """
    timeframes = [
        {
            'value': '1m',
            'label': '1 Minute',
            'minutes': 1,
            'recommended_for': ['Scalping', 'High-Frequency']
        },
        {
            'value': '5m',
            'label': '5 Minutes',
            'minutes': 5,
            'recommended_for': ['Scalping', 'Day Trading']
        },
        {
            'value': '15m',
            'label': '15 Minutes',
            'minutes': 15,
            'recommended_for': ['Day Trading', 'Scalping']
        },
        {
            'value': '1h',
            'label': '1 Hour',
            'minutes': 60,
            'recommended_for': ['Swing Trading', 'Triangular Arbitrage']
        },
        {
            'value': '4h',
            'label': '4 Hours',
            'minutes': 240,
            'recommended_for': ['Swing Trading', 'Grid Trading', 'Market Microstructure']
        },
        {
            'value': '1d',
            'label': '1 Day',
            'minutes': 1440,
            'recommended_for': ['Position Trading', 'Statistical Arbitrage', 'ICT Smart Money']
        },
        {
            'value': '1w',
            'label': '1 Week',
            'minutes': 10080,
            'recommended_for': ['Long-Term Investing']
        },
    ]

    return timeframes


@router.get("/exchanges", response_model=List[dict])
def get_available_exchanges():
    """
    사용 가능한 거래소 목록 조회

    Returns:
        거래소 목록
    """
    exchanges = [
        {
            'id': 'binance',
            'name': 'Binance',
            'description': 'World\'s largest cryptocurrency exchange',
            'supported': True
        },
        {
            'id': 'upbit',
            'name': 'Upbit',
            'description': 'Korea\'s largest cryptocurrency exchange',
            'supported': False
        },
        {
            'id': 'bithumb',
            'name': 'Bithumb',
            'description': 'Korean cryptocurrency exchange',
            'supported': False
        },
    ]

    return exchanges
