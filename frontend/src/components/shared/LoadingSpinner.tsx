import { Box, CircularProgress } from '@mui/material';

/**
 * LoadingSpinner component for displaying loading states
 *
 * @param fullHeight - If true, the spinner takes full height of its container
 * @returns A centered loading spinner component
 */
interface LoadingSpinnerProps {
  fullHeight?: boolean;
}

const LoadingSpinner = ({ fullHeight = false }: LoadingSpinnerProps) => {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: fullHeight ? '100vh' : 'auto',
        p: 4,
      }}
      data-testid="loading-spinner"
    >
      <CircularProgress color="primary" />
    </Box>
  );
};

export default LoadingSpinner;
