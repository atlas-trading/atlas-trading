import { useEffect, useRef, useState } from 'react';
import { createChart, type IChartApi, type ISeriesApi, type CandlestickData, type Time } from 'lightweight-charts';
import type { PaperTradingTrade } from '../../types/paper_trading';

interface KlineData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface CandlestickChartProps {
  klineData: KlineData[];
  trades: PaperTradingTrade[];
  onTradeClick?: (trade: PaperTradingTrade) => void;
}

export default function CandlestickChart({ klineData, trades, onTradeClick }: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const [hoveredTrade, setHoveredTrade] = useState<PaperTradingTrade | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart with Binance dark theme
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#0B0E11' },
        textColor: '#B7BDC6',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.1)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.1)' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#F0B90B',
          width: 1,
          style: 2,
          labelBackgroundColor: '#F0B90B',
        },
        horzLine: {
          color: '#F0B90B',
          width: 1,
          style: 2,
          labelBackgroundColor: '#F0B90B',
        },
      },
      rightPriceScale: {
        borderColor: '#2B3139',
        scaleMargins: {
          top: 0.1,
          bottom: 0.2,
        },
      },
      timeScale: {
        borderColor: '#2B3139',
        timeVisible: true,
        secondsVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: 500,
    });

    // Create candlestick series
    const candlestickSeries = (chart as any).addCandlestickSeries({
      upColor: '#0ECB81',
      downColor: '#F6465D',
      borderUpColor: '#0ECB81',
      borderDownColor: '#F6465D',
      wickUpColor: '#0ECB81',
      wickDownColor: '#F6465D',
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  // Update candlestick data
  useEffect(() => {
    if (!candlestickSeriesRef.current || klineData.length === 0) return;

    const formattedData: CandlestickData[] = klineData.map((candle) => ({
      time: (candle.time / 1000) as Time, // Convert ms to seconds
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));

    candlestickSeriesRef.current.setData(formattedData);

    // Fit content to visible range
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [klineData]);

  // Update trade markers
  useEffect(() => {
    if (!candlestickSeriesRef.current || trades.length === 0) return;

    const markers = trades
      .filter((trade) => trade.entry_price !== null)
      .map((trade) => {
        const isBuy = trade.side === 'buy';
        const timestamp = new Date(trade.timestamp).getTime() / 1000; // Convert to seconds

        return {
          time: timestamp as Time,
          position: isBuy ? ('belowBar' as const) : ('aboveBar' as const),
          color: isBuy ? '#0ECB81' : '#F6465D',
          shape: isBuy ? ('arrowUp' as const) : ('arrowDown' as const),
          text: isBuy ? 'BUY' : 'SELL',
          size: 1.5,
        };
      });

    (candlestickSeriesRef.current as any).setMarkers(markers);
  }, [trades]);

  // Handle marker click (approximation via mouse position)
  useEffect(() => {
    if (!chartContainerRef.current || !chartRef.current) return;

    const handleClick = (event: MouseEvent) => {
      if (!chartRef.current) return;

      const rect = chartContainerRef.current!.getBoundingClientRect();
      const x = event.clientX - rect.left;

      // Get time from x coordinate
      const timeScale = chartRef.current.timeScale();
      const coordinate = timeScale.coordinateToTime(x);

      if (coordinate) {
        const clickTime = coordinate as number;

        // Find closest trade within 60 seconds
        const clickedTrade = trades.find((trade) => {
          const tradeTime = new Date(trade.timestamp).getTime() / 1000;
          return Math.abs(tradeTime - clickTime) < 60;
        });

        if (clickedTrade && onTradeClick) {
          onTradeClick(clickedTrade);
        }
      }
    };

    const handleMouseMove = (event: MouseEvent) => {
      if (!chartRef.current) return;

      const rect = chartContainerRef.current!.getBoundingClientRect();
      const x = event.clientX - rect.left;

      const timeScale = chartRef.current.timeScale();
      const coordinate = timeScale.coordinateToTime(x);

      if (coordinate) {
        const mouseTime = coordinate as number;

        // Find trade near cursor
        const nearbyTrade = trades.find((trade) => {
          const tradeTime = new Date(trade.timestamp).getTime() / 1000;
          return Math.abs(tradeTime - mouseTime) < 30;
        });

        if (nearbyTrade) {
          setHoveredTrade(nearbyTrade);
          setTooltipPos({ x: event.clientX - rect.left, y: event.clientY - rect.top });
        } else {
          setHoveredTrade(null);
          setTooltipPos(null);
        }
      }
    };

    chartContainerRef.current.addEventListener('click', handleClick);
    chartContainerRef.current.addEventListener('mousemove', handleMouseMove);

    return () => {
      if (chartContainerRef.current) {
        chartContainerRef.current.removeEventListener('click', handleClick);
        chartContainerRef.current.removeEventListener('mousemove', handleMouseMove);
      }
    };
  }, [trades, onTradeClick]);

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <div ref={chartContainerRef} style={{ width: '100%', height: '500px' }} />

      {/* Trade Hover Tooltip */}
      {hoveredTrade && tooltipPos && (
        <div
          style={{
            position: 'absolute',
            left: tooltipPos.x + 10,
            top: tooltipPos.y - 80,
            background: 'rgba(30, 35, 41, 0.95)',
            border: '1px solid var(--border-primary)',
            borderRadius: '8px',
            padding: '12px 16px',
            pointerEvents: 'none',
            zIndex: 1000,
            minWidth: '200px',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Trade #{hoveredTrade.id}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span
              style={{
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 700,
                background: hoveredTrade.side === 'buy' ? 'rgba(14, 203, 129, 0.15)' : 'rgba(246, 70, 93, 0.15)',
                color: hoveredTrade.side === 'buy' ? '#0ECB81' : '#F6465D',
                textTransform: 'uppercase',
              }}
            >
              {hoveredTrade.side}
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              {hoveredTrade.symbol}
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
            <div>
              <div style={{ color: 'var(--text-tertiary)', fontSize: '10px', marginBottom: '2px' }}>Entry</div>
              <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                ${hoveredTrade.entry_price?.toFixed(2) || '-'}
              </div>
            </div>
            <div>
              <div style={{ color: 'var(--text-tertiary)', fontSize: '10px', marginBottom: '2px' }}>Qty</div>
              <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                {hoveredTrade.quantity.toFixed(4)}
              </div>
            </div>
          </div>
          {hoveredTrade.pnl !== null && (
            <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid var(--border-primary)' }}>
              <div style={{ color: 'var(--text-tertiary)', fontSize: '10px', marginBottom: '2px' }}>PnL</div>
              <div
                style={{
                  fontSize: '14px',
                  fontWeight: 700,
                  color: hoveredTrade.pnl >= 0 ? '#0ECB81' : '#F6465D',
                }}
              >
                {hoveredTrade.pnl >= 0 ? '+' : ''}${hoveredTrade.pnl.toFixed(2)}
                {hoveredTrade.pnl_percent !== null && (
                  <span style={{ fontSize: '11px', marginLeft: '6px', opacity: 0.8 }}>
                    ({hoveredTrade.pnl_percent >= 0 ? '+' : ''}{hoveredTrade.pnl_percent.toFixed(2)}%)
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
