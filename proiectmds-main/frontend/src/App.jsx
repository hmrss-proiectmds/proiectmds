import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import GameLobby from './pages/GameLobby';
import GameBoard from './pages/GameBoard';
import Leaderboard from './pages/Leaderboard';
import MatchHistory from './pages/MatchHistory';
import Spectate from './pages/Spectate';
import Agents from './pages/Agents';
import ChatWidget from './components/ChatWidget';
import './index.css';

/**
 * Inner app layout — Navbar is only shown when authenticated.
 */
function AppLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="auth-page">
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <>
      {user && <Navbar />}
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
        <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />

        {/* Protected routes */}
        <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/play" element={<ProtectedRoute><GameLobby /></ProtectedRoute>} />
        <Route path="/game/:gameId" element={<ProtectedRoute><GameBoard /></ProtectedRoute>} />
        <Route path="/leaderboard" element={<ProtectedRoute><Leaderboard /></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute><MatchHistory /></ProtectedRoute>} />
        <Route path="/spectate" element={<ProtectedRoute><Spectate /></ProtectedRoute>} />
        <Route path="/spectate/:gameId" element={<ProtectedRoute><Spectate /></ProtectedRoute>} />
        <Route path="/agents" element={<ProtectedRoute><Agents /></ProtectedRoute>} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <ChatWidget />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppLayout />
      </AuthProvider>
    </BrowserRouter>
  );
}
