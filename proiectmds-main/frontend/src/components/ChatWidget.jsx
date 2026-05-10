import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './ChatWidget.css';

const API_URL = '/api/chat';

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hey there! 👋 I\'m GameBot, your platform assistant. Ask me anything about Chess, Poker, or how things work around here!' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: 'user', content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: updatedMessages }),
      });
      const data = await res.json();
      const reply = data.reply || 'Sorry, I couldn\'t process that.';
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Oops, I had trouble connecting. Please try again!' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* ── Chat Panel ── */}
      <div className={`chat-panel ${isOpen ? 'chat-panel-open' : ''}`}>
        <div className="chat-header">
          <div className="chat-header-info">
            <span className="chat-avatar">🤖</span>
            <div>
              <span className="chat-title">GameBot</span>
              <span className="chat-subtitle">Platform Assistant</span>
            </div>
          </div>
          <button className="chat-close-btn" onClick={() => setIsOpen(false)}>
            ✕
          </button>
        </div>

        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`chat-msg chat-msg-${msg.role}`}>
              {msg.role === 'assistant' && <span className="chat-msg-avatar">🤖</span>}
              <div className="chat-msg-bubble">
                {msg.role === 'assistant' ? (
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                ) : (
                  msg.content
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="chat-msg chat-msg-assistant">
              <span className="chat-msg-avatar">🤖</span>
              <div className="chat-msg-bubble chat-typing">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <input
            ref={inputRef}
            type="text"
            className="chat-input"
            placeholder="Ask me anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button
            className="chat-send-btn"
            onClick={sendMessage}
            disabled={!input.trim() || loading}
          >
            ➤
          </button>
        </div>
      </div>

      {/* ── Toggle Button ── */}
      <button
        className={`chat-toggle-btn ${isOpen ? 'chat-toggle-hidden' : ''}`}
        onClick={() => setIsOpen(true)}
        title="Chat with GameBot"
      >
        <span className="chat-toggle-icon">💬</span>
        <span className="chat-toggle-pulse" />
      </button>
    </>
  );
}
