import React, { useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthContext, AuthProvider } from './context/AuthContext';
import Login from './pages/Login';
import MentorDashboard from './pages/MentorDashboard';
import StudentDashboard from './pages/StudentDashboard';
import CoordinatorDashboard from './pages/CoordinatorDashboard';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles/App.css';

function ProtectedRoute({ component: Component, requiredRole }) {
  const { isAuthenticated, user, loading } = useContext(AuthContext);

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  if (requiredRole && user?.role !== requiredRole) {
    return <Navigate to="/login" />;
  }

  return <Component />;
}

function AppContent() {
  const { isAuthenticated, loading } = useContext(AuthContext);

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/mentor"
        element={<ProtectedRoute component={MentorDashboard} requiredRole="mentor" />}
      />
      <Route
        path="/student"
        element={<ProtectedRoute component={StudentDashboard} requiredRole="student" />}
      />
      <Route
        path="/coordinator"
        element={<ProtectedRoute component={CoordinatorDashboard} requiredRole="coordinator" />}
      />
      <Route
        path="/"
        element={isAuthenticated ? <Navigate to="/mentor" /> : <Navigate to="/login" />}
      />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;
