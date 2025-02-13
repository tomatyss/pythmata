import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  MenuItem,
  FormControl,
  FormHelperText,
  InputLabel,
  Select,
  Switch,
  FormControlLabel,
} from '@mui/material';
import { useState, useEffect } from 'react';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

export interface ProcessVariableDefinition {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'date';
  required: boolean;
  defaultValue?: string | number | boolean | Date;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    options?: (string | number)[];
  };
  label: string;
  description?: string;
}

export type ProcessVariableValue = {
  type: 'string' | 'number' | 'boolean' | 'date';
  value: string | number | boolean | string; // date is stored as ISO string
};

export interface ProcessVariables {
  [key: string]: ProcessVariableValue;
}

interface ProcessVariablesDialogProps {
  open: boolean;
  processId: string;
  variableDefinitions: ProcessVariableDefinition[];
  onClose: () => void;
  onSubmit: (variables: ProcessVariables) => void;
}

const ProcessVariablesDialog = ({
  open,
  processId,
  variableDefinitions,
  onClose,
  onSubmit,
}: ProcessVariablesDialogProps) => {
  const [values, setValues] = useState<
    Record<string, string | number | boolean | Date | null>
  >({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Reset form when dialog closes or process changes
  useEffect(() => {
    if (!open) {
      setValues({});
      setErrors({});
    } else {
      // Initialize with default values
      const defaultValues: Record<
        string,
        string | number | boolean | Date | null
      > = {};
      variableDefinitions.forEach((def) => {
        if (def.defaultValue !== undefined) {
          defaultValues[def.name] = def.defaultValue;
        }
      });
      setValues(defaultValues);
    }
  }, [open, processId, variableDefinitions]);

  const validateField = (
    def: ProcessVariableDefinition,
    value: string | number | boolean | Date | null | undefined
  ): string => {
    if (def.required && (value === undefined || value === '')) {
      return `${def.label} is required`;
    }

    if (value !== undefined && value !== '' && def.validation) {
      if (def.type === 'number') {
        const numValue = Number(value);
        if (def.validation.min !== undefined && numValue < def.validation.min) {
          return `Value must be at least ${def.validation.min}`;
        }
        if (def.validation.max !== undefined && numValue > def.validation.max) {
          return `Value must be at most ${def.validation.max}`;
        }
      }
      if (def.type === 'string' && def.validation.pattern) {
        const regex = new RegExp(def.validation.pattern);
        if (!regex.test(String(value))) {
          return `Invalid format`;
        }
      }
      if (
        def.validation.options &&
        typeof value !== 'object' &&
        !def.validation.options.includes(value as string | number)
      ) {
        return `Value must be one of: ${def.validation.options.join(', ')}`;
      }
    }

    return '';
  };

  const handleChange = (
    name: string,
    value: string | number | boolean | Date | null,
    def: ProcessVariableDefinition
  ) => {
    setValues((prev) => {
      if (value === null || value === undefined) {
        const newValues = { ...prev };
        delete newValues[name];
        return newValues;
      }
      return { ...prev, [name]: value };
    });
    const error = validateField(def, value);
    setErrors((prev) => ({ ...prev, [name]: error }));
  };

  const handleSubmit = () => {
    // Validate all fields
    const newErrors: Record<string, string> = {};
    variableDefinitions.forEach((def) => {
      const error = validateField(def, values[def.name]);
      if (error) {
        newErrors[def.name] = error;
      }
    });

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // Convert values to proper types
    const processedValues = variableDefinitions.reduce((acc, def) => {
      const rawValue = values[def.name];

      if (rawValue !== undefined && rawValue !== null && rawValue !== '') {
        let processedValue;
        switch (def.type) {
          case 'number':
            processedValue = Number(rawValue);
            break;
          case 'boolean':
            processedValue = Boolean(rawValue);
            break;
          case 'date':
            processedValue =
              rawValue instanceof Date ? rawValue.toISOString() : rawValue;
            break;
          default:
            processedValue = rawValue;
        }

        acc[def.name] = {
          type: def.type,
          value: processedValue as string | number | boolean,
        };
      }
      return acc;
    }, {} as ProcessVariables);

    onSubmit(processedValues);
    handleClose();
  };

  const handleClose = () => {
    setValues({});
    setErrors({});
    onClose();
  };

  const renderField = (def: ProcessVariableDefinition) => {
    const value = values[def.name];
    const error = errors[def.name];

    switch (def.type) {
      case 'boolean':
        return (
          <FormControlLabel
            control={
              <Switch
                checked={!!value}
                onChange={(e) => handleChange(def.name, e.target.checked, def)}
              />
            }
            label={def.label}
          />
        );

      case 'date':
        return (
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <DatePicker<Date>
              label={def.label}
              value={value instanceof Date ? value : null}
              onChange={(newValue) =>
                handleChange(def.name, newValue || null, def)
              }
              slotProps={{
                textField: {
                  fullWidth: true,
                  error: !!error,
                  helperText: error || def.description,
                },
              }}
            />
          </LocalizationProvider>
        );

      case 'number':
        return (
          <TextField
            label={def.label}
            type="number"
            value={value?.toString() || ''}
            onChange={(e) =>
              handleChange(def.name, Number(e.target.value), def)
            }
            error={!!error}
            helperText={error || def.description}
            fullWidth
            inputProps={{
              min: def.validation?.min,
              max: def.validation?.max,
              step: 'any',
            }}
          />
        );

      default:
        if (def.validation?.options) {
          return (
            <FormControl fullWidth error={!!error}>
              <InputLabel>{def.label}</InputLabel>
              <Select
                value={value?.toString() || ''}
                label={def.label}
                onChange={(e) => {
                  const value = e.target.value;
                  if (def.validation?.options?.includes(value)) {
                    handleChange(def.name, value, def);
                  }
                }}
              >
                {def.validation.options.map((option) => (
                  <MenuItem key={option} value={option}>
                    {option}
                  </MenuItem>
                ))}
              </Select>
              {(error || def.description) && (
                <FormHelperText>{error || def.description}</FormHelperText>
              )}
            </FormControl>
          );
        }

        return (
          <TextField
            label={def.label}
            value={value || ''}
            onChange={(e) => handleChange(def.name, e.target.value, def)}
            error={!!error}
            helperText={error || def.description}
            fullWidth
          />
        );
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Start Process</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Process Variables
          </Typography>
          {variableDefinitions.map((def) => (
            <Box key={def.name} sx={{ mt: 2 }}>
              {renderField(def)}
            </Box>
          ))}
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
