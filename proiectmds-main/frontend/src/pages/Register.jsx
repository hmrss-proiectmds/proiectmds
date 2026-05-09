import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Auth.css';

const roles = [
  { value: 'human_player', label: '👤 Human Player', desc: 'Play games, climb the leaderboard' },
  { value: 'ai_developer', label: '👨‍💻 AI Developer', desc: 'Upload & test AI agents' },
  { value: 'ai_agent_owner', label: '🤖 AI Agent Owner', desc: 'Deploy & manage autonomous bots' },
];

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: '',
    username: '',
    password: '',
    role: 'human_player',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const update = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(form.email, form.username, form.password, form.role);
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page animate-fade-in">
      <div className="auth-card card">
        <div className="auth-header">
          <span className="auth-icon">🚀</span>
          <h1 className="auth-title">Create account</h1>
          <p className="auth-subtitle">Join the AI Game Simulation Platform</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label className="form-label" htmlFor="reg-email">Email</label>
            <input
              id="reg-email"
              className="form-input"
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={update('email')}
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="reg-username">Username</label>
            <input
              id="reg-username"
              className="form-input"
              type="text"
              placeholder="Choose a username"
              value={form.username}
              onChange={update('username')}
              required
              minLength={3}
              maxLength={50}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="reg-password">Password</label>
            <input
              id="reg-password"
              className="form-input"
              type="password"
              placeholder="Min 8 characters"
              value={form.password}
              onChange={update('password')}
              required
              minLength={8}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="reg-role">I am a…</label>
            <div className="role-selector">
              {roles.map((r) => (
                <label
                  key={r.value}
                  className={`role-option card-hover ${
                    form.role === r.value ? 'role-option-active' : ''
                  }`}
                >
                  <input
                    type="radio"
                    name="role"
                    value={r.value}
                    checked={form.role === r.value}
                    onChange={update('role')}
                    className="role-radio"
                  />
                  <span className="role-label">{r.label}</span>
                  <span className="role-desc">{r.desc}</span>
                </label>
              ))}
            </div>
          </div>

          <button
            id="register-submit"
            type="submit"
            className="btn btn-primary btn-lg w-full"
            disabled={loading}
          >
            {loading ? <span className="spinner" /> : 'Create Account'}
          </button>
        </form>

        <p className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
