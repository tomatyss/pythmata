import { useState, useCallback } from 'react';
import { Alert, AlertColor, Snackbar } from '@mui/material';

interface NotificationState {
  open: boolean;
  message: string;
  severity: AlertColor;
}

const useNotification = () => {
  const [notification, setNotification] = useState<NotificationState>({
    open: false,
    message: '',
    severity: 'info',
  });

  const showNotification = useCallback(
    (message: string, severity: AlertColor = 'info') => {
      setNotification({
        open: true,
        message,
        severity,
      });
    },
    []
  );

  const hideNotification = useCallback(() => {
    setNotification((prev) => ({
      ...prev,
      open: false,
    }));
  }, []);

  const NotificationComponent = useCallback(() => {
    return (
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={hideNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={hideNotification}
          severity={notification.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    );
  }, [notification.open, notification.severity, notification.message]);

  return {
    showNotification,
    hideNotification,
    NotificationComponent,
    // Helper methods for common notifications
    showSuccess: useCallback(
      (message: string) => showNotification(message, 'success'),
      [showNotification]
    ),
    showError: useCallback(
      (message: string) => showNotification(message, 'error'),
      [showNotification]
    ),
    showWarning: useCallback(
      (message: string) => showNotification(message, 'warning'),
      [showNotification]
    ),
    showInfo: useCallback(
      (message: string) => showNotification(message, 'info'),
      [showNotification]
    ),
  };
};

export default useNotification;
