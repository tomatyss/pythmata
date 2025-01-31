import { Box, CircularProgress, Typography } from '@mui/material';

interface LoadingSpinnerProps {
  message?: string;
  size?: number;
  fullHeight?: boolean;
}

const LoadingSpinner = ({
  message = 'Loading...',
  size = 40,
  fullHeight = false,
}: LoadingSpinnerProps) => {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: fullHeight ? 'calc(100vh - 64px)' : '400px',
        gap: 2,
      }}
    >
      <CircularProgress size={size} />
      {message && (
        <Typography color="textSecondary" variant="body1">
          {message}
        </Typography>
      )}
    </Box>
  );
};

export default LoadingSpinner;
