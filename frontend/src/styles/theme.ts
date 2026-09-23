import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: { main: '#2563eb', dark: '#1d4ed8' },
    secondary: { main: '#7c3aed' },
    background: { default: '#f4f6f8', paper: '#ffffff' },
    error: { main: '#dc2626' },
    warning: { main: '#f59e0b' },
    success: { main: '#16a34a' },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: "'Roboto', 'Segoe UI', system-ui, sans-serif",
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700 },
    h3: { fontWeight: 600 },
    h4: { fontWeight: 600 },
  },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { textTransform: 'none', fontWeight: 600 } },
    },
    MuiPaper: {
      styleOverrides: { root: { backgroundImage: 'none' } },
    },
  },
});

export default theme;

/** Design tokens for incident status/priority, shared across components and CSS. */
export const STATUS_COLORS: Record<string, string> = {
  open: '#2563eb',
  in_progress: '#f59e0b',
  blocked: '#dc2626',
  resolved: '#16a34a',
  closed: '#6b7280',
};

export const PRIORITY_COLORS: Record<string, string> = {
  low: '#6b7280',
  medium: '#2563eb',
  high: '#f59e0b',
  critical: '#dc2626',
};
