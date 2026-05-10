import { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import './Agents.css';

const GAME_TYPES = ['chess', 'poker'];

const STATUS_BADGE = {
  active: 'badge-success',
  paused: 'badge-accent',
  banned: 'badge-error',
};

const MODE_ICON = {
  webhook: '🔗',
  upload: '📄',
};

function timeAgo(dateStr) {
  if (!dateStr) return '—';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function getToken() {
  return localStorage.getItem('access_token');
}

// ── Rename inline component ───────────────────────────────────────────────────
function RenameRow({ agent, onDone }) {
  const [value, setValue] = useState(agent.name);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSave = async () => {
    if (!value.trim()) return;
    setSaving(true);
    setError('');
    try {
      const form = new FormData();
      form.append('name', value.trim());
      const res = await fetch(`/api/agents/${agent.id}/rename`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Rename failed.');
      onDone(data.name);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <div className="agents-rename-row">
      <input
        className="agents-input agents-rename-input"
        value={value}
        maxLength={100}
        autoFocus
        onChange={e => setValue(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter') handleSave();
          if (e.key === 'Escape') onDone(null);
        }}
      />
      <button className="btn btn-primary agents-rename-btn" onClick={handleSave} disabled={saving}>✓</button>
      <button className="btn agents-rename-btn agents-rename-cancel" onClick={() => onDone(null)}>✕</button>
      {error && <span className="agents-error" style={{ fontSize: '0.75rem' }}>{error}</span>}
    </div>
  );
}

// ── Webhook registration form ─────────────────────────────────────────────────
function WebhookForm({ onSuccess }) {
  const [name, setName] = useState('');
  const [gameType, setGameType] = useState('chess');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [continuous, setContinuous] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    if (!name.trim()) { setError('Agent name is required.'); return; }
    if (!webhookUrl.startsWith('http://') && !webhookUrl.startsWith('https://')) {
      setError('Webhook URL must start with http:// or https://'); return;
    }
    setSaving(true);
    try {
      const data = await api.post('/api/agents/register-webhook', {
        name: name.trim(),
        game_type: gameType,
        webhook_url: webhookUrl,
        continuous_queue: continuous,
      });
      setSuccess(`Agent "${data.name}" registered!`);
      setName(''); setWebhookUrl(''); setContinuous(false);
      onSuccess(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="agents-form" onSubmit={handleSubmit}>
      <div className="agents-form-row">
        <label className="agents-label">
          Agent Name
          <input
            className="agents-input"
            type="text"
            placeholder="e.g. MyChessBot"
            value={name}
            onChange={e => setName(e.target.value)}
            maxLength={100}
            required
          />
        </label>
        <label className="agents-label">
          Game Type
          <select className="agents-input" value={gameType} onChange={e => setGameType(e.target.value)}>
            {GAME_TYPES.map(g => <option key={g} value={g}>{g.charAt(0).toUpperCase() + g.slice(1)}</option>)}
          </select>
        </label>
      </div>

      <label className="agents-label">
        Webhook URL
        <input
          className="agents-input"
          type="url"
          placeholder="https://your-server.com/agent/move"
          value={webhookUrl}
          onChange={e => setWebhookUrl(e.target.value)}
          required
        />
        <span className="agents-input-hint">
          The platform will POST game state JSON here when it's your agent's turn.
          Respond with <code>{`{"move": "e2e4"}`}</code>
        </span>
      </label>

      <label className="agents-checkbox-label">
        <input
          type="checkbox"
          checked={continuous}
          onChange={e => setContinuous(e.target.checked)}
        />
        <span>Continuous queue — automatically re-queue after each match ends</span>
      </label>

      {error && <p className="agents-error">{error}</p>}
      {success && <p className="agents-success">{success}</p>}

      <button className="btn btn-primary agents-submit" type="submit" disabled={saving}>
        {saving ? 'Registering…' : '🔗 Register Webhook Agent'}
      </button>
    </form>
  );
}

// ── Upload form ───────────────────────────────────────────────────────────────
function UploadForm({ onSuccess }) {
  const [name, setName] = useState('');
  const [gameType, setGameType] = useState('chess');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileRef = useRef();

  const handleUpload = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    if (!file) { setError('Please select a .py file.'); return; }
    if (!name.trim()) { setError('Agent name is required.'); return; }

    const form = new FormData();
    form.append('name', name.trim());
    form.append('game_type', gameType);
    form.append('file', file);

    setUploading(true);
    try {
      const res = await fetch('/api/agents/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed.');
      setSuccess(`Agent "${data.name}" uploaded!`);
      setName(''); setFile(null);
      if (fileRef.current) fileRef.current.value = '';
      onSuccess(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <form className="agents-form" onSubmit={handleUpload}>
      <div className="agents-form-row">
        <label className="agents-label">
          Agent Name
          <input
            className="agents-input"
            type="text"
            placeholder="e.g. MyChessBot"
            value={name}
            onChange={e => setName(e.target.value)}
            maxLength={100}
            required
          />
        </label>
        <label className="agents-label">
          Game Type
          <select className="agents-input" value={gameType} onChange={e => setGameType(e.target.value)}>
            {GAME_TYPES.map(g => <option key={g} value={g}>{g.charAt(0).toUpperCase() + g.slice(1)}</option>)}
          </select>
        </label>
      </div>

      <label className="agents-label">
        Script File (.py only, max 1 MB)
        <div
          className={`agents-dropzone ${file ? 'agents-dropzone--has-file' : ''}`}
          onClick={() => fileRef.current?.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) setFile(f); }}
        >
          {file ? `📄 ${file.name}` : 'Click or drag & drop a .py file here'}
        </div>
        <input ref={fileRef} type="file" accept=".py" style={{ display: 'none' }} onChange={e => setFile(e.target.files[0] || null)} />
      </label>

      {error && <p className="agents-error">{error}</p>}
      {success && <p className="agents-success">{success}</p>}

      <button className="btn btn-primary agents-submit" type="submit" disabled={uploading}>
        {uploading ? 'Uploading…' : '📤 Upload Agent Script'}
      </button>
    </form>
  );
}

// ── Agent card ────────────────────────────────────────────────────────────────
function AgentCard({ agent, onUpdated, onDeleted }) {
  const [renaming, setRenaming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [queueing, setQueueing] = useState(false);
  const [queueMsg, setQueueMsg] = useState('');

  const handleEnqueue = async () => {
    setQueueing(true);
    setQueueMsg('');
    try {
      const res = await api.post('/api/matchmaking/queue/agent', {
        agent_id: agent.id,
        game_type: agent.game_type,
      });
      if (res.status === 'removed') {
        onUpdated({ ...agent, in_queue: false });
        setQueueMsg('Removed');
      } else {
        onUpdated({ ...agent, in_queue: true });
        setQueueMsg('In queue! ⚔️');
      }
      setTimeout(() => setQueueMsg(''), 3000);
    } catch (err) {
      setQueueMsg('Error');
      setTimeout(() => setQueueMsg(''), 3000);
    } finally {
      setQueueing(false);
    }
  };

  const handleRenameComplete = (newName) => {
    setRenaming(false);
    if (newName) onUpdated({ ...agent, name: newName });
  };

  const handleToggleContinuous = async () => {
    setToggling(true);
    try {
      const res = await fetch(`/api/agents/${agent.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ continuous_queue: !agent.continuous_queue }),
      });
      const updated = await res.json();
      if (res.ok) onUpdated(updated);
    } catch {
      // ignore
    } finally {
      setToggling(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) { setDeleteConfirm(true); return; }
    setDeleting(true);
    try {
      await fetch(`/api/agents/${agent.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      onDeleted(agent.id);
    } catch {
      setDeleting(false);
    }
  };

  return (
    <div className="card agents-agent-card" id={`agent-card-${agent.id}`}>
      <div className="agents-agent-header">
        <span className="agents-agent-icon">{agent.game_type === 'chess' ? '♟️' : '🃏'}</span>
        <div className="agents-agent-name-block">
          {renaming ? (
            <RenameRow agent={agent} onDone={handleRenameComplete} />
          ) : (
            <div className="agents-name-row">
              <div className="agents-agent-name">{agent.name}</div>
              <button className="agents-rename-trigger" title="Rename" onClick={() => setRenaming(true)}>✏️</button>
            </div>
          )}
          <div className="agents-agent-meta">
            {MODE_ICON[agent.integration_mode] || '🤖'} {agent.integration_mode} · {agent.game_type}
          </div>
        </div>
        <span className={`badge ${STATUS_BADGE[agent.status] || 'badge-accent'} agents-status-badge`}>
          {agent.status}
        </span>
      </div>

      {agent.webhook_url && (
        <div className="agents-webhook-url" title={agent.webhook_url}>
          🔗 {agent.webhook_url.length > 50 ? agent.webhook_url.slice(0, 47) + '…' : agent.webhook_url}
        </div>
      )}

      <div className="agents-agent-stats">
        <span>⭐ {agent.elo_rating} ELO</span>
        <span>🕒 {timeAgo(agent.created_at)}</span>
      </div>

      <div className="agents-agent-actions">
        {agent.in_game_id ? (
          <button
            className="btn btn-sm btn-accent agents-action-btn"
            onClick={() => window.location.href = `/game/${agent.in_game_id}`}
            title="Spectate the live match"
          >
            🔴 Spectate Match
          </button>
        ) : (
          <button
            className={`btn btn-sm ${agent.in_queue ? 'btn-ghost' : 'btn-primary'} agents-action-btn`}
            onClick={handleEnqueue}
            disabled={queueing || agent.status !== 'active'}
            title="Send agent to matchmaking queue or remove it"
          >
            {queueMsg || (agent.in_queue ? '❌ Unqueue' : '⚔️ Find Match')}
          </button>
        )}

        {/* Continuous queue toggle — only for webhook agents */}
        {agent.integration_mode === 'webhook' && (
          <button
            className={`btn btn-sm ${agent.continuous_queue ? 'btn-primary' : 'btn-ghost'} agents-action-btn`}
            title="Toggle continuous queue mode"
            onClick={handleToggleContinuous}
            disabled={toggling}
          >
            {agent.continuous_queue ? '🔄 Auto-queue ON' : '🔄 Auto-queue OFF'}
          </button>
        )}

        <button
          className={`btn btn-sm ${deleteConfirm ? 'btn-error' : 'btn-ghost'} agents-action-btn`}
          onClick={handleDelete}
          disabled={deleting}
        >
          {deleteConfirm ? (deleting ? 'Deleting…' : '⚠️ Confirm delete') : '🗑️ Delete'}
        </button>
        {deleteConfirm && (
          <button className="btn btn-sm btn-ghost agents-action-btn" onClick={() => setDeleteConfirm(false)}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function Agents() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('webhook'); // 'webhook' | 'upload'

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const data = await api.get('/api/agents/');
      setAgents(Array.isArray(data) ? data : []);
    } catch {
      setAgents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAgents(); }, []);

  const handleNewAgent = (newAgent) => {
    setAgents(prev => [newAgent, ...prev]);
  };

  const handleUpdated = (updated) => {
    setAgents(prev => prev.map(a => a.id === updated.id ? updated : a));
  };

  const handleDeleted = (id) => {
    setAgents(prev => prev.filter(a => a.id !== id));
  };

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">🤖 My Agents</h1>
        <p className="page-subtitle">Register webhook agents or upload Python scripts to compete on the platform.</p>
      </div>

      {/* Registration tabs */}
      <div className="card agents-upload-card">
        <div className="agents-tabs">
          <button
            id="tab-webhook"
            className={`agents-tab ${activeTab === 'webhook' ? 'agents-tab--active' : ''}`}
            onClick={() => setActiveTab('webhook')}
          >
            🔗 Register Webhook Agent
          </button>
          <button
            id="tab-upload"
            className={`agents-tab ${activeTab === 'upload' ? 'agents-tab--active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            📤 Upload Python Script
          </button>
        </div>

        <div className="agents-tab-content">
          {activeTab === 'webhook' ? (
            <WebhookForm onSuccess={handleNewAgent} />
          ) : (
            <UploadForm onSuccess={handleNewAgent} />
          )}
        </div>
      </div>

      {/* Agent list */}
      <div className="agents-list-section">
        <h2 className="agents-section-title">
          🤖 My Registered Agents
          <span className="agents-count-badge">{agents.length}</span>
        </h2>
        {loading ? (
          <div className="spinner spinner-lg" style={{ margin: '2rem auto' }} />
        ) : agents.length === 0 ? (
          <p className="agents-empty">No agents yet. Register or upload your first one above!</p>
        ) : (
          <div className="agents-grid">
            {agents.map(agent => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onUpdated={handleUpdated}
                onDeleted={handleDeleted}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
