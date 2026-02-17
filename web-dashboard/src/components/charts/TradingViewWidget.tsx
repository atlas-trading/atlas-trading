import { useEffect, useRef } from 'react';

interface TradingViewWidgetProps {
  symbol: string;
  interval?: string;
  theme?: 'light' | 'dark';
  height?: number;
}

export default function TradingViewWidget({
  symbol,
  interval = '1',
  theme = 'dark',
  height = 600,
}: TradingViewWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Clear previous widget
    containerRef.current.innerHTML = '';

    // Convert symbol format: BTCUSDT -> BINANCE:BTCUSDT
    const tvSymbol = `BINANCE:${symbol.replace('/', '')}`;

    // Convert interval: 1m -> 1, 5m -> 5, 1h -> 60, 1d -> D
    const intervalMap: Record<string, string> = {
      '1m': '1',
      '5m': '5',
      '15m': '15',
      '1h': '60',
      '4h': '240',
      '1d': 'D',
    };
    const tvInterval = intervalMap[interval] || '1';

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/tv.js';
    script.async = true;
    script.onload = () => {
      if (typeof (window as any).TradingView !== 'undefined') {
        new (window as any).TradingView.widget({
          container_id: containerRef.current!.id,
          width: '100%',
          height: height,
          symbol: tvSymbol,
          interval: tvInterval,
          timezone: 'Asia/Seoul',
          theme: theme,
          style: '1',
          locale: 'en',
          toolbar_bg: '#0B0E11',
          enable_publishing: false,
          hide_side_toolbar: false,
          allow_symbol_change: true,
          details: true,
          hotlist: true,
          calendar: false,
          studies: [
            'MASimple@tv-basicstudies',
            'RSI@tv-basicstudies',
          ],
          show_popup_button: true,
          popup_width: '1000',
          popup_height: '650',
          support_host: 'https://www.tradingview.com',
        });
      }
    };

    document.head.appendChild(script);

    return () => {
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
    };
  }, [symbol, interval, theme, height]);

  return (
    <div
      ref={containerRef}
      id={`tradingview_${Math.random().toString(36).substring(7)}`}
      style={{ width: '100%', height: `${height}px` }}
    />
  );
}
