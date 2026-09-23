import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import Paper from '@mui/material/Paper';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Link from '@mui/material/Link';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import { register } from '../services/authService';
import { ApiError } from '../services/apiClient';
import ErrorAlert from '../components/common/ErrorAlert';
import AuthBackground from '../components/common/AuthBackground';
import '../styles/auth.css';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await register({ email, password, full_name: fullName });
      setSuccess(true);
      setTimeout(() => navigate('/login'), 1200);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to register.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-shell">
      <AuthBackground />
      <Paper elevation={2} className="auth-card">
        <Typography variant="h5" className="auth-title">
          Create your account
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, textAlign: 'center' }}>
          Use your @acme.inc email address to report and track facility issues.
        </Typography>
        <ErrorAlert message={error} />
        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Account created! Redirecting to sign in...
          </Alert>
        )}
        <form onSubmit={handleSubmit} className="flex-col">
          <TextField
            label="Full name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            required
            fullWidth
            autoFocus
          />
          <TextField
            label="Email"
            type="email"
            placeholder="you@acme.inc"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            fullWidth
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
            {isSubmitting ? <CircularProgress size={22} color="inherit" /> : 'Register'}
          </Button>
        </form>
        <Typography variant="body2" className="auth-footer">
          Already have an account? <Link component={RouterLink} to="/login">Sign in</Link>
        </Typography>
      </Paper>
    </div>
  );
}
