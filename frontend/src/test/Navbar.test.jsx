import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Default: no user logged in
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ user: null, logout: vi.fn() }),
}));

import Navbar from '../components/Navbar';

describe('Navbar component (logged-out)', () => {
  it('renders the brand name', () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>
    );
    expect(screen.getByText(/GamePlatform/i)).toBeInTheDocument();
  });

  it('shows Login and Register links when no user is logged in', () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>
    );
    expect(screen.getByRole('link', { name: /login/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /register/i })).toBeInTheDocument();
  });

  it('does not show a logout button when no user is logged in', () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>
    );
    expect(screen.queryByRole('button', { name: /logout/i })).not.toBeInTheDocument();
  });
});
