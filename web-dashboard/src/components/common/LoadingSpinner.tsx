// Loading spinner component
interface LoadingSpinnerProps {
  fullScreen?: boolean;
}

export default function LoadingSpinner({ fullScreen = false }: LoadingSpinnerProps) {
  const spinnerStyle = {
    border: '3px solid var(--border-primary)',
    borderTop: '3px solid var(--color-binance)',
    borderRadius: '50%',
    width: '40px',
    height: '40px',
    animation: 'spin 1s linear infinite',
  };

  const containerStyle = fullScreen
    ? {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
      }
    : {
        display: 'flex',
        justifyContent: 'center',
        padding: '40px',
      };

  return (
    <div style={containerStyle}>
      <div style={spinnerStyle}></div>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
