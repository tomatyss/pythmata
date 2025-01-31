import { Box, Button, Typography } from '@mui/material';
import { Error as ErrorIcon } from '@mui/icons-material';

interface ErrorMessageProps {
  message?: string;
  error?: Error | string;
  onRetry?: () => void;
  fullHeight?: boolean;
}

const ErrorMessage = ({
  message = 'An error occurred',
  error,
  onRetry,
  fullHeight = false,
}: ErrorMessageProps) => {
  const displayMessage = error
    ? typeof error === 'string'
      ? error
      : error.message || message
    : message;

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: fullHeight ? 'calc(100vh - 64px)' : '400px',
        gap: 2,
        p: 3,
        textAlign: 'center',
      }}
    >
      <ErrorIcon color="error" sx={{ fontSize: 48 }} />
      <Typography variant="h6" color="error" gutterBottom>
        {displayMessage}
      </Typography>
      {onRetry && (
        <Button
          variant="contained"
          color="primary"
          onClick={onRetry}
          sx={{ mt: 2 }}
        >
          Try Again
        </Button>
      )}
    </Box>
  );
};

export default ErrorMessage;
