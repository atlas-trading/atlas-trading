# TradingView-Style Candlestick Chart Components

## Overview

TradingView 스타일의 전문적인 캔들스틱 차트 컴포넌트를 구현했습니다. 이 컴포넌트들은 Paper Trading 페이지에서 실시간 시장 데이터와 거래 내역을 시각화하는 데 사용됩니다.

## Components

### 1. CandlestickChart

**파일:** `/src/components/charts/CandlestickChart.tsx`

TradingView의 `lightweight-charts` 라이브러리를 사용한 전문적인 캔들스틱 차트 컴포넌트입니다.

#### Features

- **Binance 다크모드 테마**
  - Background: #0B0E11
  - 상승 캔들: #0ECB81 (초록)
  - 하락 캔들: #F6465D (빨강)
  - 그리드: rgba(255, 255, 255, 0.1)

- **거래 마커 표시**
  - 매수: 초록색 위쪽 화살표 (↑)
  - 매도: 빨간색 아래쪽 화살표 (↓)
  - 마커에 마우스 호버 시 거래 정보 툴팁 표시
  - 마커 클릭 시 상세 패널 열기

- **인터랙티브 기능**
  - 크로스헤어 (Crosshair)
  - 줌 & 패닝
  - 실시간 가격 스케일
  - 반응형 디자인

#### Props

```typescript
interface CandlestickChartProps {
  // 캔들스틱 데이터 (Binance API 형식)
  klineData: Array<{
    time: number;      // 타임스탬프 (밀리초)
    open: number;      // 시가
    high: number;      // 고가
    low: number;       // 저가
    close: number;     // 종가
  }>;

  // 거래 내역 배열
  trades: PaperTradingTrade[];

  // 거래 마커 클릭 시 콜백
  onTradeClick?: (trade: PaperTradingTrade) => void;
}
```

#### Usage

```tsx
import { CandlestickChart } from '../components/charts';

function MyComponent() {
  const [selectedTrade, setSelectedTrade] = useState(null);

  return (
    <CandlestickChart
      klineData={klineData}
      trades={trades}
      onTradeClick={setSelectedTrade}
    />
  );
}
```

---

### 2. TradeDetailPanel

**파일:** `/src/components/paper_trading/TradeDetailPanel.tsx`

선택된 거래의 상세 정보를 표시하는 사이드 패널 컴포넌트입니다.

#### Features

- **슬라이드 애니메이션**
  - 오른쪽에서 부드럽게 나타남
  - 닫기 버튼으로 숨김

- **상세 정보 표시**
  - Symbol, Side (매수/매도)
  - Entry Price / Exit Price
  - Quantity
  - PnL (손익) 및 PnL % - 그라디언트 카드로 강조
  - Commission (수수료)
  - Slippage (슬리피지)
  - Stop Loss / Take Profit
  - Exit Reason (청산 사유)
  - Holding Time (포지션 유지 시간)
  - Executed At (실행 시간)

- **시각적 디자인**
  - 수익: 초록색 그라디언트 카드
  - 손실: 빨간색 그라디언트 카드
  - Binance 다크모드 테마 일관성 유지

#### Props

```typescript
interface TradeDetailPanelProps {
  trade: PaperTradingTrade | null;  // 표시할 거래 (null이면 숨김)
  onClose: () => void;               // 닫기 콜백
}
```

#### Usage

```tsx
import { TradeDetailPanel } from '../components/paper_trading';

function MyComponent() {
  const [selectedTrade, setSelectedTrade] = useState(null);

  return (
    <>
      {/* Your main content */}

      <TradeDetailPanel
        trade={selectedTrade}
        onClose={() => setSelectedTrade(null)}
      />
    </>
  );
}
```

---

### 3. ChartSection

**파일:** `/src/components/paper_trading/ChartSection.tsx`

CandlestickChart와 TradeDetailPanel을 통합한 올인원 컴포넌트입니다.

#### Features

- CandlestickChart와 TradeDetailPanel 자동 연결
- 차트 제목 및 설명 포함
- Card 컴포넌트로 래핑되어 일관된 스타일

#### Props

```typescript
interface ChartSectionProps {
  klineData: KlineData[];           // 캔들스틱 데이터
  trades: PaperTradingTrade[];      // 거래 내역
  symbol: string;                   // 심볼 (예: "BTCUSDT")
}
```

#### Usage

```tsx
import { ChartSection } from '../components/paper_trading';

function PaperTrading() {
  return (
    <ChartSection
      klineData={klineData}
      trades={recentTrades}
      symbol={sessionData.symbol}
    />
  );
}
```

---

## Installation

```bash
npm install lightweight-charts --legacy-peer-deps
```

---

## Integration Guide

### Step 1: Binance API에서 Kline 데이터 가져오기

```typescript
const fetchKlineData = async (symbol: string, interval: string = '5m', limit: number = 200) => {
  try {
    const response = await fetch(
      `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`
    );
    const data = await response.json();

    const formattedData = data.map((kline: any) => ({
      time: kline[0],           // 타임스탬프 (ms)
      open: parseFloat(kline[1]),
      high: parseFloat(kline[2]),
      low: parseFloat(kline[3]),
      close: parseFloat(kline[4]),
    }));

    return formattedData;
  } catch (error) {
    console.error('Failed to fetch kline data:', error);
    return [];
  }
};
```

### Step 2: PaperTrading.tsx에 통합

```typescript
import { ChartSection } from '../components/paper_trading';
import { useState, useEffect } from 'react';

export default function PaperTrading() {
  const [klineData, setKlineData] = useState([]);

  // 세션이 로드되면 kline 데이터 가져오기
  useEffect(() => {
    if (sessionData) {
      fetchKlineData(sessionData.symbol, '5m', 200)
        .then(setKlineData);
    }
  }, [sessionData]);

  return (
    <div>
      {/* 기존 UI */}

      {/* 차트 섹션 추가 */}
      {sessionData && (
        <ChartSection
          klineData={klineData}
          trades={recentTrades}
          symbol={sessionData.symbol}
        />
      )}
    </div>
  );
}
```

### Step 3: 실시간 업데이트 (선택사항)

WebSocket으로 실시간 캔들 업데이트:

```typescript
useEffect(() => {
  if (!sessionData) return;

  const ws = new WebSocket(
    `wss://stream.binance.com:9443/ws/${sessionData.symbol.toLowerCase()}@kline_5m`
  );

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const kline = data.k;

    setKlineData(prev => {
      const newData = [...prev];
      const lastCandle = newData[newData.length - 1];

      // 마지막 캔들 업데이트
      if (lastCandle && lastCandle.time === kline.t) {
        newData[newData.length - 1] = {
          time: kline.t,
          open: parseFloat(kline.o),
          high: parseFloat(kline.h),
          low: parseFloat(kline.l),
          close: parseFloat(kline.c),
        };
      } else {
        // 새 캔들 추가
        newData.push({
          time: kline.t,
          open: parseFloat(kline.o),
          high: parseFloat(kline.h),
          low: parseFloat(kline.l),
          close: parseFloat(kline.c),
        });
      }

      return newData;
    });
  };

  return () => ws.close();
}, [sessionData]);
```

---

## Design Philosophy

### Color Palette

프로젝트의 Binance 다크모드 테마를 일관되게 사용:

```css
/* Backgrounds */
--bg-primary: #0B0E11;
--bg-secondary: #1E2329;
--bg-tertiary: #181A20;

/* Status Colors */
--color-success: #0ECB81;  /* 상승 / 매수 */
--color-danger: #F6465D;   /* 하락 / 매도 */
--color-binance: #F0B90B;  /* 강조 */

/* Text */
--text-primary: #EAECEF;
--text-secondary: #B7BDC6;
--text-tertiary: #848E9C;
```

### Typography

- **제목**: 14px, 600 weight, uppercase, letter-spacing
- **값 (대형)**: 32px, 700 weight
- **값 (중형)**: 18px, 700 weight
- **메타데이터**: 11px, tertiary color

### Spacing

- 카드 내부 패딩: 24px
- 섹션 간격: 24px
- 요소 간격: 12-16px
- 그리드 갭: 16px

---

## Advanced Features (추가 개발 가능)

### 1. 타임프레임 선택기

```tsx
const [timeframe, setTimeframe] = useState('5m');

<div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
  {['1m', '5m', '15m', '1h', '4h', '1d'].map(tf => (
    <button
      key={tf}
      onClick={() => setTimeframe(tf)}
      className={timeframe === tf ? 'btn-primary' : 'btn-secondary'}
    >
      {tf}
    </button>
  ))}
</div>
```

### 2. 기술적 지표 추가

```typescript
// EMA 라인 추가
const emaSeries = chart.addLineSeries({
  color: '#F0B90B',
  lineWidth: 2,
  title: 'EMA 20',
});

emaSeries.setData(emaData);
```

### 3. 거래 구간 시각화

```typescript
// Entry에서 Exit까지 선 그리기
const drawTradeLine = (trade) => {
  if (trade.exit_price) {
    const lineSeries = chart.addLineSeries({
      color: trade.pnl >= 0 ? '#0ECB81' : '#F6465D',
      lineWidth: 1,
      lineStyle: 2, // dashed
    });

    lineSeries.setData([
      { time: trade.entry_time, value: trade.entry_price },
      { time: trade.exit_time, value: trade.exit_price },
    ]);
  }
};
```

### 4. 차트 스크린샷 내보내기

```typescript
const exportChartImage = () => {
  if (chartRef.current) {
    const canvas = chartContainerRef.current.querySelector('canvas');
    const image = canvas.toDataURL('image/png');

    const link = document.createElement('a');
    link.download = `chart-${Date.now()}.png`;
    link.href = image;
    link.click();
  }
};
```

---

## Files Created

1. `/src/components/charts/CandlestickChart.tsx` - 메인 차트 컴포넌트
2. `/src/components/paper_trading/TradeDetailPanel.tsx` - 거래 상세 패널
3. `/src/components/paper_trading/ChartSection.tsx` - 통합 섹션 컴포넌트
4. `/src/components/charts/index.ts` - 차트 컴포넌트 export
5. `/src/components/paper_trading/index.ts` - Paper Trading 컴포넌트 export (업데이트)
6. `/src/examples/PaperTradingWithChart.example.tsx` - 사용 예제

---

## Testing

컴포넌트 테스트 방법:

```bash
# TypeScript 컴파일 확인
npm run build

# 개발 서버 실행
npm run dev
```

---

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## Performance Considerations

1. **대량 데이터**: 200-500개 캔들까지 부드럽게 렌더링
2. **메모리**: 차트 인스턴스는 컴포넌트 언마운트 시 자동 정리
3. **리렌더링**: useRef로 차트 인스턴스 관리하여 불필요한 리렌더링 방지
4. **실시간 업데이트**: WebSocket 연결은 cleanup 함수에서 닫기

---

## Troubleshooting

### 차트가 표시되지 않음

- `klineData` 배열이 비어있지 않은지 확인
- `time` 값이 유효한 타임스탬프(밀리초)인지 확인
- 브라우저 콘솔에서 에러 확인

### 마커가 표시되지 않음

- `trades` 배열에 `entry_price`가 null이 아닌지 확인
- `timestamp` 형식이 ISO 8601인지 확인
- 거래 시간이 캔들 데이터 범위 내에 있는지 확인

### TypeScript 에러

```bash
npm install lightweight-charts --legacy-peer-deps
```

---

## License

이 컴포넌트들은 Atlas Trading 프로젝트의 일부입니다.

---

## Support

문제가 발생하면 프로젝트 이슈 트래커에 보고해주세요.
