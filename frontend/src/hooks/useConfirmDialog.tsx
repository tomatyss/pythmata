import { useState, useCallback } from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';

interface ConfirmDialogOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  confirmColor?: 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning';
}

interface ConfirmDialogState extends ConfirmDialogOptions {
  isOpen: boolean;
  resolve: ((value: boolean) => void) | null;
}

const defaultOptions: Partial<ConfirmDialogOptions> = {
  title: 'Confirm Action',
  confirmText: 'Confirm',
  cancelText: 'Cancel',
  confirmColor: 'primary',
};

const useConfirmDialog = () => {
  const [dialogState, setDialogState] = useState<ConfirmDialogState>({
    isOpen: false,
    message: '',
    resolve: null,
    ...defaultOptions,
  });

  const confirm = useCallback(
    (options: ConfirmDialogOptions): Promise<boolean> => {
      return new Promise((resolve) => {
        setDialogState({
          ...defaultOptions,
          ...options,
          isOpen: true,
          resolve,
        });
      });
    },
    []
  );

  const handleClose = useCallback(
    (confirmed: boolean) => {
      setDialogState((prev) => ({ ...prev, isOpen: false }));
      dialogState.resolve?.(confirmed);
    },
    [dialogState.resolve]
  );

  const ConfirmDialog = useCallback(() => {
    const {
      isOpen,
      title,
      message,
      confirmText,
      cancelText,
      confirmColor,
    } = dialogState;

    return (
      <Dialog
        open={isOpen}
        onClose={() => handleClose(false)}
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
      >
        <DialogTitle id="confirm-dialog-title">{title}</DialogTitle>
        <DialogContent>
          <DialogContentText id="confirm-dialog-description">
            {message}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => handleClose(false)}>{cancelText}</Button>
          <Button
            onClick={() => handleClose(true)}
            color={confirmColor}
            variant="contained"
            autoFocus
          >
            {confirmText}
          </Button>
        </DialogActions>
      </Dialog>
    );
  }, [dialogState, handleClose]);

  return {
    confirm,
    ConfirmDialog,
    // Helper methods for common confirmations
    confirmDelete: useCallback(
      (itemName: string) =>
        confirm({
          title: 'Confirm Deletion',
          message: `Are you sure you want to delete ${itemName}? This action cannot be undone.`,
          confirmText: 'Delete',
          confirmColor: 'error',
        }),
      [confirm]
    ),
    confirmSuspend: useCallback(
      (itemName: string) =>
        confirm({
          title: 'Confirm Suspension',
          message: `Are you sure you want to suspend ${itemName}?`,
          confirmText: 'Suspend',
          confirmColor: 'warning',
        }),
      [confirm]
    ),
    confirmResume: useCallback(
      (itemName: string) =>
        confirm({
          title: 'Confirm Resume',
          message: `Are you sure you want to resume ${itemName}?`,
          confirmText: 'Resume',
          confirmColor: 'success',
        }),
      [confirm]
    ),
  };
};

export default useConfirmDialog;
