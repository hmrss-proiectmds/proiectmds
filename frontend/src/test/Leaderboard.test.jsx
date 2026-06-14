import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock api client so we don't hit a real server
vi.mock('../api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

// Mock auth hook — no logged-in user needed for most tests
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ user: null }),
}));

import { api } from '../api/client';
import Leaderboard from '../pages/Leaderboard';

function renderLeaderboard() {
  return render(
    <MemoryRouter>
      <Leaderboard />
    </MemoryRouter>
  );
}

describe('Leaderboard page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    api.get.mockResolvedValue({ entries: [] });
    renderLeaderboard();
    expect(screen.getByText(/leaderboard/i)).toBeInTheDocument();
  });

  it('shows "no players" message when entries list is empty', async () => {
    api.get.mockResolvedValue({ entries: [] });
    renderLeaderboard();
    await waitFor(() => {
      expect(screen.getByText(/no players registered yet/i)).toBeInTheDocument();
    });
  });

  it('renders a row for each leaderboard entry', async () => {
    api.get.mockResolvedValue({
      entries: [
        { rank: 1, username: 'Alice', role: 'human_player', elo_rating: 1400, entity_type: 'human' },
        { rank: 2, username: 'BotAlpha', role: 'agent', elo_rating: 1300, entity_type: 'agent' },
      ],
    });
    renderLeaderboard();
    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
      expect(screen.getByText('BotAlpha')).toBeInTheDocument();
    });
  });

  it('renders ELO values in the table', async () => {
    api.get.mockResolvedValue({
      entries: [
        { rank: 1, username: 'Alice', role: 'human_player', elo_rating: 1550, entity_type: 'human' },
      ],
    });
    renderLeaderboard();
    await waitFor(() => {
      expect(screen.getByText('1550')).toBeInTheDocument();
    });
  });

  it('shows the "Show AI Agents" toggle checkbox', async () => {
    api.get.mockResolvedValue({ entries: [] });
    renderLeaderboard();
    expect(screen.getByLabelText(/show ai agents/i)).toBeInTheDocument();
  });
});
