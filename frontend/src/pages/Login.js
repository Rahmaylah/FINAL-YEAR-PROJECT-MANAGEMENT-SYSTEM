import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import '../styles/Login.css';
import nitLogo from '../assets/nit.png';

function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Use the context's login function which handles the API call correctly
      const result = await login(username, password);
      
      if (result.success) {
        console.log('Login successful');
        // Get the updated user from context after login
        setTimeout(() => {
          // Small delay to let context update
          const storedUser = JSON.parse(localStorage.getItem('user'));
          if (storedUser) {
            if (storedUser.role === 'mentor') {
              navigate('/mentor');
            } else if (storedUser.role === 'student') {
              navigate('/student');
            } else if (storedUser.role === 'coordinator') {
              navigate('/coordinator');
            }
          }
        }, 100);
      } else {
        // Display specific error messages based on error type
        let displayError = result.error || 'Login failed';
        
        if (result.errorType === 'network') {
          displayError = '⚠️ ' + result.error;
        } else if (result.errorType === 'auth') {
          displayError = '❌ ' + result.error;
        }
        
        setError(displayError);
      }
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message || 'Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };



  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <h1>CCT</h1>
          {/* <p>Final Year Project Management System</p> */}
          <img src={nitLogo} alt="NIT Logo" className="nit-logo" />
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group mb-3">
            <label htmlFor="username" className="form-label">Username</label>
            <input
              type="text"
              className="form-control"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
            />
          </div>

          <div className="form-group mb-3">
            <label htmlFor="password" className="form-label">Password</label>
            <input
              type="password"
              className="form-control"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
            />
          </div>

          {error && (
            <div className="alert alert-danger" role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary w-100 login-btn"
            disabled={loading}
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default Login;
