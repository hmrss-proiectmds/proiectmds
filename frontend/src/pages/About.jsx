import React from 'react';
import './About.css';

export default function About() {
  return (
    <div className="about-container">
      <header className="about-header">
        <h1>About GamePlatform</h1>
        <p>
          The ultimate environment for testing, developing, and competing with AI game agents.
          Where strategy meets artificial intelligence.
        </p>
      </header>

      <div className="about-grid">
        <div className="about-card">
          <span className="about-card-icon">🤖</span>
          <h3>AI Agent Integration</h3>
          <p>
            Easily upload and deploy your own AI agents. We support multiple games and provide 
            standardized APIs for seamless integration.
          </p>
        </div>

        <div className="about-card">
          <span className="about-card-icon">⚡</span>
          <h3>Massive Simulations</h3>
          <p>
            Run thousands of games in parallel using our high-performance simulation engine 
            to gather statistical data on agent performance.
          </p>
        </div>

        <div className="about-card">
          <span className="about-card-icon">🏆</span>
          <h3>Competitive Leaderboard</h3>
          <p>
            Compete against other developers. Our ELO-based ranking system ensures fair 
            and accurate measurement of agent skill.
          </p>
        </div>

        <div className="about-card">
          <span className="about-card-icon">👁️</span>
          <h3>Real-time Spectating</h3>
          <p>
            Watch games as they happen. Visualize the decision-making process of AI 
            agents in real-time with our interactive game boards.
          </p>
        </div>
      </div>

      <div className="about-mission">
        <h2>Our Mission</h2>
        <p>
          We aim to provide a robust platform for researchers, students, and hobbyists to 
          explore the boundaries of game AI. By providing the infrastructure for hosting, 
          simulating, and ranking agents, we allow developers to focus on what matters most: 
          creating better algorithms.
        </p>
      </div>

      <div className="tech-stack">
        <h2>Built with Modern Tech</h2>
        <div className="tech-icons">
          <div className="tech-item">
            <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/react/react-original.svg" alt="React" width="40" height="40" />
            <span>React</span>
          </div>
          <div className="tech-item">
            <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg" alt="Python" width="40" height="40" />
            <span>Python</span>
          </div>
          <div className="tech-item">
            <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/fastapi/fastapi-original.svg" alt="FastAPI" width="40" height="40" />
            <span>FastAPI</span>
          </div>
          <div className="tech-item">
            <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/postgresql/postgresql-original.svg" alt="PostgreSQL" width="40" height="40" />
            <span>PostgreSQL</span>
          </div>
          <div className="tech-item">
            <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/redis/redis-original.svg" alt="Redis" width="40" height="40" />
            <span>Redis</span>
          </div>
          <div className="tech-item">
            <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/docker/docker-original.svg" alt="Docker" width="40" height="40" />
            <span>Docker</span>
          </div>
        </div>
      </div>
    </div>
  );
}
