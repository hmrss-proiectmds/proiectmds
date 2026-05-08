import './Placeholder.css';

export default function MatchHistory() {
  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">📊 Match History</h1>
        <p className="page-subtitle">Your complete game timeline with replays and analysis</p>
      </div>
      <div className="placeholder-card card">
        <span className="placeholder-icon">🕐</span>
        <h2>Coming in Phase 3</h2>
        <p className="text-muted">
          Match history will show a paginated list of past games with opponents,
          results, ELO changes, and downloadable replays.
        </p>
      </div>
    </div>
  );
}
