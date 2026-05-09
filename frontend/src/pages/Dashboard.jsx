import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Dashboard.css';

const roleConfigs = {
  human_player: {
    icon: '👤',
    title: 'Player Dashboard',
    cards: [
      { icon: '⚔️', title: 'Play a Game', desc: 'Challenge AI opponents or other players', link: '/play', tag: 'Available' },
      { icon: '👁️', title: 'Spectate', desc: 'Watch live AI vs AI matches', link: '/spectate', tag: 'Available' },
      { icon: '🏆', title: 'Leaderboard', desc: 'See global ELO rankings', link: '/leaderboard', tag: 'Available' },
      { icon: '📊', title: 'Match History', desc: 'Review your past games', link: '/history', tag: 'Available' },
    ],
  },
  ai_developer: {
    icon: '👨‍💻',
    title: 'Developer Dashboard',
    cards: [
      { icon: '📤', title: 'Upload Agent', desc: 'Deploy a new AI agent to the platform', link: '/agents', tag: 'Coming soon' },
      { icon: '🧪', title: 'Bulk Simulations', desc: 'Run thousands of headless games', link: '/simulations', tag: 'Coming soon' },
      { icon: '🔍', title: 'Decision Logs', desc: 'Debug your agent\'s move decisions', link: '/logs', tag: 'Coming soon' },
      { icon: '🏆', title: 'Leaderboard', desc: 'Check your agent rankings', link: '/leaderboard', tag: 'Available' },
    ],
  },
  ai_agent_owner: {
    icon: '🤖',
    title: 'Agent Owner Dashboard',
    cards: [
      { icon: '🤖', title: 'My Agents', desc: 'Manage your deployed agents', link: '/agents', tag: 'Coming soon' },
      { icon: '🔄', title: 'Continuous Queue', desc: 'Configure auto-play settings', link: '/agents', tag: 'Coming soon' },
      { icon: '📈', title: 'Performance', desc: 'Track agent ELO and win rates', link: '/leaderboard', tag: 'Available' },
      { icon: '📊', title: 'Match History', desc: 'Review agent match records', link: '/history', tag: 'Available' },
    ],
  },
  admin: {
    icon: '🛡️',
    title: 'Admin Dashboard',
    cards: [
      { icon: '🖥️', title: 'Moderation', desc: 'Monitor and manage active agents', link: '/admin', tag: 'Coming soon' },
      { icon: '📊', title: 'Platform Stats', desc: 'Live server metrics & load', link: '/admin', tag: 'Coming soon' },
      { icon: '🏆', title: 'Leaderboard', desc: 'Global rankings overview', link: '/leaderboard', tag: 'Available' },
      { icon: '👥', title: 'Users', desc: 'Manage platform users', link: '/admin', tag: 'Coming soon' },
    ],
  },
};

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const config = roleConfigs[user.role] || roleConfigs.human_player;

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div className="dashboard-welcome">
          <span className="dashboard-welcome-icon">{config.icon}</span>
          <div>
            <h1 className="page-title">{config.title}</h1>
            <p className="page-subtitle">
              Welcome back, <strong>{user.username}</strong> — you have{' '}
              <span className="text-accent font-mono">{user.elo_rating}</span> ELO
            </p>
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        {config.cards.map((card, i) => (
          <div
            key={i}
            className="card card-hover dashboard-card"
            style={{ animationDelay: `${i * 80}ms` }}
            onClick={() => card.tag === 'Available' && navigate(card.link)}
          >
            <span className="dashboard-card-icon">{card.icon}</span>
            <h3 className="dashboard-card-title">{card.title}</h3>
            <p className="dashboard-card-desc">{card.desc}</p>
            <span className={`badge ${card.tag === 'Available' ? 'badge-success' : 'badge-accent'}`}>
              {card.tag}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
