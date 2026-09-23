import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import Paper from '@mui/material/Paper';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Link from '@mui/material/Link';
import CircularProgress from '@mui/material/CircularProgress';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../services/apiClient';
import ErrorAlert from '../components/common/ErrorAlert';
import AuthBackground from '../components/common/AuthBackground';
import '../styles/auth.css';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ email, password });
      navigate('/');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to sign in.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-shell">
      <AuthBackground />
      <Paper elevation={2} className="auth-card">
        <Typography variant="h5" className="auth-title">
          Sign in to ACME Facilities
        </Typography>
        <ErrorAlert message={error} />
        <form onSubmit={handleSubmit} className="flex-col">
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            fullWidth
            autoFocus
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            fullWidth
          />
          <Button type="submit" variant="contained" size="large" disabled={isSubmitting} fullWidth>
            {isSubmitting ? <CircularProgress size={22} color="inherit" /> : 'Sign in'}
          </Button>
        </form>
        <Typography variant="body2" className="auth-footer">
          Need an account? <Link component={RouterLink} to="/register">Register</Link>
        </Typography>
      </Paper>
    </div>
  );
}
