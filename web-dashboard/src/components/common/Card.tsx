// Card component for wrapping content
interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export default function Card({ children, className = '' }: CardProps) {
  return (
    <div
      className={`card ${className}`}
      style={{
        background: 'var(--bg-secondary)',
        borderRadius: '8px',
        padding: '20px',
        border: '1px solid var(--border-primary)',
      }}
    >
      {children}
    </div>
  );
}
