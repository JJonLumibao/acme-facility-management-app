import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', gap: 2 }}>
      <Typography variant="h3">404</Typography>
      <Typography color="text.secondary">Page not found.</Typography>
      <Button component={Link} to="/" variant="contained">
        Back to dashboard
      </Button>
    </Box>
  );
}
