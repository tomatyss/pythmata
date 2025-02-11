import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
} from '@mui/material';
import { useState, useEffect } from 'react';

export interface ProcessVariables
  extends Record<string, string | number | boolean | null> {
  order_id: string;
  amount: number;
}

interface ProcessVariablesDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (variables: ProcessVariables) => void;
}

const ProcessVariablesDialog = ({
  open,
  onClose,
  onSubmit,
}: ProcessVariablesDialogProps) => {
  const [amount, setAmount] = useState<string>('');
  const [error, setError] = useState<string>('');

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      setAmount('');
      setError('');
    }
  }, [open]);

  const handleSubmit = () => {
    // Validate amount
    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError('Please enter a valid amount greater than 0');
      return;
    }

    // Create variables object
    const variables: ProcessVariables = {
      order_id: `ORDER-${Date.now()}`,
      amount: numAmount,
    };

    onSubmit(variables);
    handleClose();
  };

  const handleClose = () => {
    setAmount('');
    setError('');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Start Process</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Order Details
          </Typography>
          <TextField
            label="Amount"
            type="number"
            value={amount}
            onChange={(e) => {
              setAmount(e.target.value);
              setError('');
            }}
            error={!!error}
            helperText={error}
            fullWidth
            sx={{ mt: 1 }}
            inputProps={{ min: 0, step: 0.01 }}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button onClick={handleSubmit} variant="contained" color="primary">
          Start
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ProcessVariablesDialog;
