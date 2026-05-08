import './Placeholder.css';

export default function Leaderboard() {
  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">🏆 Leaderboard</h1>
        <p className="page-subtitle">Cross-entity ELO rankings — humans and AI agents on one scale</p>
      </div>
      <div className="placeholder-card card">
        <span className="placeholder-icon">📊</span>
        <h2>Coming in Phase 3</h2>
        <p className="text-muted">
          The leaderboard will display a unified ranking table with ELO ratings,
          filterable by entity type (Human / AI) and game type.
        </p>
      </div>
    </div>
  );
}
