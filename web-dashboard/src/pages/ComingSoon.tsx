interface ComingSoonProps {
  page: string;
}

export default function ComingSoon({ page }: ComingSoonProps) {
  return (
    <div className="page-container">
      <div className="coming-soon-container">
        <div className="coming-soon-content">
          <h1 className="text-4xl font-bold mb-4">{page}</h1>
          <p className="text-xl opacity-70 mb-8">Coming Soon</p>
          <p className="text-sm opacity-50">
            This feature is under development and will be available soon.
          </p>
        </div>
      </div>
    </div>
  );
}
