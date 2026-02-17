"""전략 시그널 시각화 스크립트"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.backtesting import BacktestEngine, DataFetcher
from app.strategies.ict_smart_money import ICTSmartMoneyStrategy
from app.strategies.statistical_arbitrage import StatisticalArbitrageStrategy
from app.strategies.market_microstructure import MarketMicrostructureStrategy
from app.strategies.adaptive_grid_trading import AdaptiveGridTradingStrategy
from app.strategies.triangular_arbitrage import TriangularArbitrageStrategy


def visualize_strategy(strategy_class, strategy_name, symbol='BTCUSDT', timeframe='1h', days=180):
    """전략의 매매 시그널을 시각화"""

    print(f"\n{'=' * 100}")
    print(f"📊 전략 시각화: {strategy_name} on {symbol} ({timeframe})")
    print(f"{'=' * 100}\n")

    # 데이터 다운로드
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    fetcher = DataFetcher(exchange_id="binance")
    df = fetcher.fetch_ohlcv(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
    )

    if df.empty or len(df) < 100:
        print(f"❌ 데이터 부족: {len(df)} 캔들")
        return None

    print(f"✅ 데이터 다운로드 완료: {len(df)} 캔들")

    # 전략 초기화
    strategy = strategy_class(symbol=symbol)
    df = strategy.prepare_data(df)

    # 백테스팅 실행
    engine = BacktestEngine(initial_capital=10000, commission=0.0004)
    results = engine.run(df=df, strategy=strategy, symbol=symbol, timeframe=timeframe)

    trades = results.get('trades', [])

    if not trades:
        print(f"⚠️  거래 없음")
        return None

    print(f"✅ 백테스트 완료: {len(trades)} 거래")
    print(f"   수익률: {results['total_return']:.2f}%")
    print(f"   승률: {results['win_rate']:.1f}%")

    # 시각화
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    fig.suptitle(f'{strategy_name} - {symbol} ({timeframe})', fontsize=16, fontweight='bold')

    # 1. 가격 차트 + 매매 시그널
    ax1.plot(df['timestamp'], df['close'], label='Close Price', color='#2E86AB', linewidth=1.5, alpha=0.8)

    # 진입/청산 포인트 표시
    for trade in trades:
        entry_time = trade['entry_time']
        exit_time = trade['exit_time']
        entry_price = trade['entry_price']
        exit_price = trade['exit_price']
        pnl = trade['pnl']

        # 진입 (녹색 화살표)
        ax1.scatter(entry_time, entry_price, color='green', marker='^', s=100, zorder=5, alpha=0.8)

        # 청산 (빨간색 또는 파란색 화살표)
        color = 'blue' if pnl > 0 else 'red'
        ax1.scatter(exit_time, exit_price, color=color, marker='v', s=100, zorder=5, alpha=0.8)

        # 거래 연결선
        ax1.plot([entry_time, exit_time], [entry_price, exit_price],
                color=color, linestyle='--', linewidth=1, alpha=0.5)

    ax1.set_ylabel('Price (USDT)', fontsize=12, fontweight='bold')
    ax1.legend(['Price', 'Entry (↑)', 'Profit Exit (↓)', 'Loss Exit (↓)'], loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_title('Price Chart with Trade Signals', fontsize=12, fontweight='bold')

    # 2. Equity Curve
    equity_df = pd.DataFrame(results['equity_curve'])
    ax2.plot(equity_df['timestamp'], equity_df['equity'], color='#06A77D', linewidth=2)
    ax2.fill_between(equity_df['timestamp'], 10000, equity_df['equity'],
                     where=(equity_df['equity'] >= 10000), color='green', alpha=0.2)
    ax2.fill_between(equity_df['timestamp'], 10000, equity_df['equity'],
                     where=(equity_df['equity'] < 10000), color='red', alpha=0.2)
    ax2.axhline(y=10000, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax2.set_ylabel('Equity (USDT)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.set_title(f'Equity Curve (Final: ${results["final_capital"]:.2f}, Return: {results["total_return"]:.2f}%)',
                 fontsize=12, fontweight='bold')

    # 3. 거래 수익 분포
    pnl_list = [t['pnl_pct'] for t in trades]
    colors = ['green' if p > 0 else 'red' for p in pnl_list]
    ax3.bar(range(len(pnl_list)), pnl_list, color=colors, alpha=0.6)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax3.set_xlabel('Trade Number', fontsize=12, fontweight='bold')
    ax3.set_ylabel('PnL (%)', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.set_title(f'Individual Trade PnL Distribution (Win Rate: {results["win_rate"]:.1f}%)',
                 fontsize=12, fontweight='bold')

    # 날짜 포맷
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)

    plt.tight_layout()

    # 저장
    output_dir = Path(__file__).parent.parent / 'results' / 'strategy_visualizations'
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{strategy_name.replace(' ', '_')}_{symbol}_{timeframe}.png"
    filepath = output_dir / filename
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"💾 차트 저장: {filepath}")

    plt.close()

    return filepath


def create_strategy_comparison_html():
    """전략 비교 HTML 생성"""

    html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas Trading - 전략 시각화</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: #00d4ff;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 40px;
        }
        .strategy-section {
            background: #1a1f3a;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 40px;
            border: 1px solid #2a3f5f;
        }
        .strategy-title {
            color: #00d4ff;
            font-size: 24px;
            margin-bottom: 15px;
            border-bottom: 2px solid #00d4ff;
            padding-bottom: 10px;
        }
        .strategy-description {
            color: #b0b0b0;
            margin-bottom: 20px;
            line-height: 1.6;
        }
        .doc-links {
            background: #0f1428;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .doc-links a {
            color: #00d4ff;
            text-decoration: none;
            margin-right: 20px;
        }
        .doc-links a:hover {
            text-decoration: underline;
        }
        .chart-container {
            text-align: center;
            margin-top: 20px;
        }
        .chart-container img {
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.2);
        }
        .key-points {
            background: #0f1428;
            padding: 15px 25px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .key-points h3 {
            color: #00d4ff;
            margin-top: 0;
        }
        .key-points ul {
            margin: 10px 0;
        }
        .key-points li {
            margin: 8px 0;
            line-height: 1.5;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Atlas Trading - Professional Strategies</h1>
        <p class="subtitle">프로페셔널 트레이딩 전략 시각화 가이드</p>
"""

    strategies_info = [
        {
            'name': 'ICT Smart Money Concepts',
            'description': '기관 투자자들의 주문 흐름을 분석하여 "스마트 머니"와 함께 거래하는 프로페셔널 전략입니다.',
            'key_points': [
                '✅ Order Blocks: 스마트 머니가 대량 주문을 넣은 영역',
                '✅ Fair Value Gaps (FVG): 가격 불균형 영역',
                '✅ Liquidity Raids: 스톱 헌팅 (손절 유동성 수집)',
                '✅ 진입: 유동성 레이드 + 오더블록/FVG 재테스트',
                '✅ 청산: 구조 변화, 목표가 도달, ATR 기반 손절',
            ],
            'doc': '/docs/PRO_STRATEGIES_GUIDE.md#1-ict-smart-money-concepts-strategy',
        },
        {
            'name': 'Statistical Arbitrage',
            'description': '통계적 차익거래는 Z-Score 정규화와 볼린저 밴드를 결합하여 평균회귀를 이용한 전략입니다.',
            'key_points': [
                '✅ Z-Score < -2.0: 심각한 과매도 (매수)',
                '✅ Z-Score > +2.0: 심각한 과매수 (매도)',
                '✅ ADX < 30: 강한 추세가 아님 (평균회귀 가능)',
                '✅ 진입: Z-Score 임계값 + 볼린저 밴드 끝단 + 충분한 거래량',
                '✅ 청산: Z-Score가 0 근처 복귀 (평균회귀 완료)',
            ],
            'doc': '/docs/PRO_STRATEGIES_GUIDE.md#2-statistical-arbitrage-strategy',
        },
        {
            'name': 'Market Microstructure',
            'description': '거래량 프로파일과 주문 흐름(Delta)을 분석하여 기관 투자자의 활동을 감지하는 전략입니다.',
            'key_points': [
                '✅ Volume Profile: 가격대별 거래량 분포',
                '✅ VPOC: 최대 거래량 발생 가격 (강력한 지지/저항)',
                '✅ Delta Volume: 매수량 - 매도량 (순수 수급)',
                '✅ 진입: 강한 델타 + 볼륨 노드 근처',
                '✅ 청산: 델타 반전, 다음 볼륨 노드 도달',
            ],
            'doc': '/docs/PRO_STRATEGIES_GUIDE.md#3-market-microstructure-strategy',
        },
        {
            'name': 'Adaptive Grid Trading',
            'description': '변동성에 맞춰 그리드 간격을 동적으로 조절하는 고급 그리드 전략입니다.',
            'key_points': [
                '✅ ATR 기반 그리드 간격 자동 조절',
                '✅ 트렌드 필터로 강한 추세 시 그리드 중단',
                '✅ 자동 리밸런싱 (가격 5% 이동 시)',
                '✅ 진입: 가격이 그리드 레벨 터치',
                '✅ 청산: 반대 그리드 레벨 도달',
            ],
            'doc': '/docs/PRO_STRATEGIES_GUIDE.md#4-adaptive-grid-trading-strategy',
        },
        {
            'name': 'Triangular Arbitrage',
            'description': '가격 효율성 이탈을 감지하여 초단기 평균회귀 기회를 포착하는 전략입니다.',
            'key_points': [
                '✅ Efficiency < -0.3%: 이론가보다 저평가',
                '✅ 높은 거래량: 유동성 확보',
                '✅ 좁은 스프레드: 차익거래 조건',
                '✅ 진입: 가격 효율성 이탈 + 높은 거래량',
                '✅ 청산: 5봉 이내 강제 청산 (초단타)',
            ],
            'doc': '/docs/PRO_STRATEGIES_GUIDE.md#5-triangular-arbitrage-strategy',
        },
    ]

    for info in strategies_info:
        html_content += f"""
        <div class="strategy-section">
            <h2 class="strategy-title">{info['name']}</h2>
            <p class="strategy-description">{info['description']}</p>

            <div class="doc-links">
                <strong>📚 문서:</strong>
                <a href="{info['doc']}" target="_blank">전략 가이드</a>
                <a href="/docs/BACKTEST_GUIDE.md" target="_blank">백테스트 가이드</a>
            </div>

            <div class="key-points">
                <h3>핵심 포인트</h3>
                <ul>
"""
        for point in info['key_points']:
            html_content += f"                    <li>{point}</li>\n"

        html_content += """                </ul>
            </div>

            <div class="chart-container">
                <p><em>차트는 백테스트 실행 후 생성됩니다.</em></p>
            </div>
        </div>
"""

    html_content += """
    </div>
</body>
</html>
"""

    # HTML 저장
    output_dir = Path(__file__).parent.parent / 'results' / 'strategy_visualizations'
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / 'strategies_guide.html'
    filepath.write_text(html_content, encoding='utf-8')

    print(f"\n💾 HTML 가이드 생성: {filepath}")
    return filepath


def main():
    """메인 실행"""

    print("\n" + "=" * 100)
    print("📊 전략 시각화 시스템")
    print("=" * 100)

    # HTML 가이드 생성
    html_path = create_strategy_comparison_html()

    # 각 전략 시각화
    strategies = [
        (AdaptiveGridTradingStrategy, 'Adaptive_Grid_Trading', 'BTCUSDT', '4h', 180),
        (MarketMicrostructureStrategy, 'Market_Microstructure', 'ETHUSDT', '1h', 180),
        (StatisticalArbitrageStrategy, 'Statistical_Arbitrage', 'SOLUSDT', '1d', 365),
        (ICTSmartMoneyStrategy, 'ICT_Smart_Money', 'AVAXUSDT', '4h', 365),
        (TriangularArbitrageStrategy, 'Triangular_Arbitrage', 'MATICUSDT', '1h', 90),
    ]

    generated_charts = []

    for strategy_class, name, symbol, timeframe, days in strategies:
        try:
            chart_path = visualize_strategy(strategy_class, name, symbol, timeframe, days)
            if chart_path:
                generated_charts.append((name, chart_path))
        except Exception as e:
            print(f"❌ {name} 시각화 실패: {e}")

    # 요약
    print("\n" + "=" * 100)
    print("✨ 시각화 완료")
    print("=" * 100)
    print(f"\n📁 생성된 파일:")
    print(f"   HTML 가이드: {html_path}")
    for name, path in generated_charts:
        print(f"   {name}: {path}")

    print(f"\n💡 HTML 가이드를 브라우저로 열어보세요:")
    print(f"   file://{html_path.absolute()}")


if __name__ == "__main__":
    main()
