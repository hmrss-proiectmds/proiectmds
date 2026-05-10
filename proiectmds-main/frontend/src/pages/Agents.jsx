import { useState, useEffect, useRef } from 'react';
import './Agents.css';

const GAME_TYPES = ['chess', 'poker'];
const STATUS_BADGE = {
  active: 'badge-success',
  paused: 'badge-accent',
  banned: 'badge-error',
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

export default function Agents() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  // Rename state: { [agentId]: { editing, value, saving, error } }
  const [renameState, setRenameState] = useState({});

  const startRename = (agent) =>
    setRenameState(s => ({ ...s, [agent.id]: { editing: true, value: agent.name, saving: false, error: '' } }));

  const cancelRename = (id) =>
    setRenameState(s => { const n = { ...s }; delete n[id]; return n; });

  const handleRename = async (agentId) => {
    const rs = renameState[agentId];
    if (!rs || !rs.value.trim()) return;
    setRenameState(s => ({ ...s, [agentId]: { ...s[agentId], saving: true, error: '' } }));
    try {
      const form = new FormData();
      form.append('name', rs.value.trim());
      const res = await fetch(`/api/agents/${agentId}/rename`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Rename failed.');
      setAgents(prev => prev.map(a => a.id === agentId ? { ...a, name: data.name } : a));
      cancelRename(agentId);
    } catch (err) {
      setRenameState(s => ({ ...s, [agentId]: { ...s[agentId], saving: false, error: err.message } }));
    }
  };

  // Upload form state
  const [name, setName] = useState('');
  const [gameType, setGameType] = useState('chess');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');
  const fileRef = useRef();

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/agents/', {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) setAgents(await res.json());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAgents(); }, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    setUploadError('');
    setUploadSuccess('');

    if (!file) { setUploadError('Please select a .py file.'); return; }
    if (!name.trim()) { setUploadError('Agent name is required.'); return; }

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
      setUploadSuccess(`Agent "${data.name}" uploaded successfully!`);
      setName('');
      setGameType('chess');
      setFile(null);
      if (fileRef.current) fileRef.current.value = '';
      fetchAgents();
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">My Agents</h1>
        <p className="page-subtitle">Upload Python agent scripts to compete on the platform.</p>
      </div>

      {/* Upload form */}
      <div className="card agents-upload-card">
        <h2 className="agents-section-title">📤 Upload New Agent</h2>
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
              <select
                className="agents-input"
                value={gameType}
                onChange={e => setGameType(e.target.value)}
              >
                {GAME_TYPES.map(g => (
                  <option key={g} value={g}>{g.charAt(0).toUpperCase() + g.slice(1)}</option>
                ))}
              </select>
            </label>
          </div>

          <label className="agents-label">
            Script File (.py only, max 1 MB)
            <div
              className={`agents-dropzone ${file ? 'agents-dropzone--has-file' : ''}`}
              onClick={() => fileRef.current?.click()}
              onDragOver={e => e.preventDefault()}
              onDrop={e => {
                e.preventDefault();
                const f = e.dataTransfer.files[0];
                if (f) setFile(f);
              }}
            >
              {file ? `📄 ${file.name}` : 'Click or drag & drop a .py file here'}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".py"
              style={{ display: 'none' }}
              onChange={e => setFile(e.target.files[0] || null)}
            />
          </label>

          {uploadError && <p className="agents-error">{uploadError}</p>}
          {uploadSuccess && <p className="agents-success">{uploadSuccess}</p>}

          <button className="btn btn-primary agents-submit" type="submit" disabled={uploading}>
            {uploading ? 'Uploading…' : 'Upload Agent'}
          </button>
        </form>
      </div>

      {/* Agent list */}
      <div className="agents-list-section">
        <h2 className="agents-section-title">🤖 My Uploaded Agents</h2>
        {loading ? (
          <div className="spinner spinner-lg" style={{ margin: '2rem auto' }} />
        ) : agents.length === 0 ? (
          <p className="agents-empty">No agents yet. Upload your first one above!</p>
        ) : (
          <div className="agents-grid">
            {agents.map(agent => {
              const rs = renameState[agent.id];
              return (
              <div key={agent.id} className="card agents-agent-card">
                <div className="agents-agent-header">
                  <span className="agents-agent-icon">{agent.game_type === 'chess' ? '♟️' : '🃏'}</span>
                  <div className="agents-agent-name-block">
                    {rs?.editing ? (
                      <div className="agents-rename-row">
                        <input
                          className="agents-input agents-rename-input"
                          value={rs.value}
                          maxLength={100}
                          autoFocus
                          onChange={e => setRenameState(s => ({ ...s, [agent.id]: { ...s[agent.id], value: e.target.value } }))}
                          onKeyDown={e => { if (e.key === 'Enter') handleRename(agent.id); if (e.key === 'Escape') cancelRename(agent.id); }}
                        />
                        <button className="btn btn-primary agents-rename-btn" onClick={() => handleRename(agent.id)} disabled={rs.saving}>✓</button>
                        <button className="btn agents-rename-btn agents-rename-cancel" onClick={() => cancelRename(agent.id)}>✕</button>
                        {rs.error && <span className="agents-error" style={{fontSize:'0.75rem'}}>{rs.error}</span>}
                      </div>
                    ) : (
                      <div className="agents-name-row">
                        <div className="agents-agent-name">{agent.name}</div>
                        <button className="agents-rename-trigger" title="Rename" onClick={() => startRename(agent)}>✏️</button>
                      </div>
                    )}
                    <div className="agents-agent-meta">{agent.game_type}</div>
                  </div>
                  <span className={`badge ${STATUS_BADGE[agent.status] || 'badge-accent'} agents-status-badge`}>
                    {agent.status}
                  </span>
                </div>
                <div className="agents-agent-stats">
                  <span>⭐ {agent.elo_rating} ELO</span>
                  <span>🕒 {timeAgo(agent.created_at)}</span>
                </div>
              </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
