import { ReactNode } from 'react';
import {
  FormControl,
  FormHelperText,
  FormLabel,
  Box,
  Typography,
} from '@mui/material';
import { FieldError } from 'react-hook-form';

export interface FormFieldProps {
  label?: string;
  error?: FieldError;
  required?: boolean;
  fullWidth?: boolean;
  children: ReactNode;
  helperText?: string;
}

const FormField = ({
  label,
  error,
  required = false,
  fullWidth = true,
  children,
  helperText,
}: FormFieldProps) => {
  return (
    <FormControl
      error={!!error}
      required={required}
      fullWidth={fullWidth}
      sx={{ mb: 2 }}
    >
      {label && (
        <Box sx={{ mb: 1 }}>
          <FormLabel
            component="legend"
            sx={{
              typography: 'body1',
              fontWeight: 500,
              color: error ? 'error.main' : 'text.primary',
            }}
          >
            {label}
            {!required && (
              <Typography
                component="span"
                variant="body2"
                color="text.secondary"
                sx={{ ml: 1 }}
              >
                (Optional)
              </Typography>
            )}
          </FormLabel>
        </Box>
      )}
      {children}
      {(error?.message || helperText) && (
        <FormHelperText error={!!error}>
          {error?.message || helperText}
        </FormHelperText>
      )}
    </FormControl>
  );
};

export default FormField;
