import Alert from '@mui/material/Alert';

/** Renders nothing when there's no message, otherwise a dismissible-styled error banner. */
export default function ErrorAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <Alert severity="error" sx={{ mb: 2 }}>
      {message}
    </Alert>
  );
}
