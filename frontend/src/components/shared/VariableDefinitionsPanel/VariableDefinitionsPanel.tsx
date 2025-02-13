import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Typography,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useState } from 'react';
import { ProcessVariableDefinition } from '@/types/process';

interface VariableDefinitionFormData
  extends Omit<ProcessVariableDefinition, 'validation'> {
  validation: {
    min?: string;
    max?: string;
    pattern?: string;
    options?: string;
  };
}

interface VariableDefinitionsDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (definition: ProcessVariableDefinition) => void;
  initialData?: ProcessVariableDefinition;
}

const VariableDefinitionsDialog = ({
  open,
  onClose,
  onSave,
  initialData,
}: VariableDefinitionsDialogProps) => {
  const [formData, setFormData] = useState<VariableDefinitionFormData>(() => ({
    name: initialData?.name || '',
    type: initialData?.type || 'string',
    required: initialData?.required ?? true,
    label: initialData?.label || '',
    description: initialData?.description || '',
    defaultValue: initialData?.defaultValue || '',
    validation: {
      min: initialData?.validation?.min?.toString() || '',
      max: initialData?.validation?.max?.toString() || '',
      pattern: initialData?.validation?.pattern || '',
      options: initialData?.validation?.options?.join(', ') || '',
    },
  }));

  const handleSubmit = () => {
    const validation: ProcessVariableDefinition['validation'] = {};

    if (formData.type === 'number') {
      if (formData.validation.min)
        validation.min = Number(formData.validation.min);
      if (formData.validation.max)
        validation.max = Number(formData.validation.max);
    }

    if (formData.type === 'string') {
      if (formData.validation.pattern)
        validation.pattern = formData.validation.pattern;
    }

    if (formData.validation.options) {
      validation.options = formData.validation.options
        .split(',')
        .map((opt) => opt.trim())
        .filter(Boolean);
    }

    const definition: ProcessVariableDefinition = {
      name: formData.name,
      type: formData.type,
      required: formData.required,
      label: formData.label,
      description: formData.description || undefined,
      defaultValue: formData.defaultValue || undefined,
      validation: Object.keys(validation).length > 0 ? validation : undefined,
    };

    onSave(definition);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {initialData ? 'Edit Variable' : 'Add Variable'}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
          <TextField
            label="Name"
            value={formData.name}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, name: e.target.value }))
            }
            required
            fullWidth
          />

          <TextField
            label="Label"
            value={formData.label}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, label: e.target.value }))
            }
            required
            fullWidth
          />

          <FormControl fullWidth>
            <InputLabel>Type</InputLabel>
            <Select
              value={formData.type}
              label="Type"
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  type: e.target.value as ProcessVariableDefinition['type'],
                }))
              }
            >
              <MenuItem value="string">String</MenuItem>
              <MenuItem value="number">Number</MenuItem>
              <MenuItem value="boolean">Boolean</MenuItem>
              <MenuItem value="date">Date</MenuItem>
            </Select>
          </FormControl>

          <TextField
            label="Description"
            value={formData.description}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, description: e.target.value }))
            }
            multiline
            rows={2}
            fullWidth
          />

          <TextField
            label="Default Value"
            value={formData.defaultValue}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, defaultValue: e.target.value }))
            }
            fullWidth
          />

          <FormControlLabel
            control={
              <Switch
                checked={formData.required}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    required: e.target.checked,
                  }))
                }
              />
            }
            label="Required"
          />

          <Typography variant="subtitle2" sx={{ mt: 2 }}>
            Validation Rules
          </Typography>

          {formData.type === 'number' && (
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="Min"
                type="number"
                value={formData.validation.min}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    validation: { ...prev.validation, min: e.target.value },
                  }))
                }
              />
              <TextField
                label="Max"
                type="number"
                value={formData.validation.max}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    validation: { ...prev.validation, max: e.target.value },
                  }))
                }
              />
            </Box>
          )}

          {formData.type === 'string' && (
            <TextField
              label="Pattern (regex)"
              value={formData.validation.pattern}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  validation: { ...prev.validation, pattern: e.target.value },
                }))
              }
              fullWidth
            />
          )}

          <TextField
            label="Options (comma-separated)"
            value={formData.validation.options}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                validation: { ...prev.validation, options: e.target.value },
              }))
            }
            fullWidth
            helperText="Enter allowed values separated by commas"
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSubmit} variant="contained" color="primary">
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};

interface VariableDefinitionsPanelProps {
  variables: ProcessVariableDefinition[];
  onChange: (variables: ProcessVariableDefinition[]) => void;
}

const VariableDefinitionsPanel = ({
  variables,
  onChange,
}: VariableDefinitionsPanelProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVariable, setEditingVariable] = useState<
    ProcessVariableDefinition | undefined
  >();

  const handleAdd = (variable: ProcessVariableDefinition) => {
    onChange([...variables, variable]);
  };

  const handleEdit = (variable: ProcessVariableDefinition, index: number) => {
    const newVariables = [...variables];
    newVariables[index] = variable;
    onChange(newVariables);
  };

  const handleDelete = (index: number) => {
    const newVariables = variables.filter((_, i) => i !== index);
    onChange(newVariables);
  };

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 2,
        }}
      >
        <Typography variant="h6">Process Variables</Typography>
        <Button
          startIcon={<AddIcon />}
          onClick={() => {
            setEditingVariable(undefined);
            setDialogOpen(true);
          }}
        >
          Add Variable
        </Button>
      </Box>

      <List>
        {variables.map((variable, index) => (
          <ListItem key={index} divider>
            <ListItemText
              primary={variable.label}
              secondary={
                <>
                  <Typography
                    component="span"
                    variant="body2"
                    color="text.primary"
                  >
                    {variable.name} ({variable.type})
                  </Typography>
                  {variable.description && (
                    <Typography component="p" variant="body2">
                      {variable.description}
                    </Typography>
                  )}
                </>
              }
            />
            <ListItemSecondaryAction>
              <Tooltip title="Edit">
                <IconButton
                  edge="end"
                  onClick={() => {
                    setEditingVariable(variable);
                    setDialogOpen(true);
                  }}
                >
                  <EditIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Delete">
                <IconButton edge="end" onClick={() => handleDelete(index)}>
                  <DeleteIcon />
                </IconButton>
              </Tooltip>
            </ListItemSecondaryAction>
          </ListItem>
        ))}
      </List>

      <VariableDefinitionsDialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
          setEditingVariable(undefined);
        }}
        onSave={(variable) => {
          if (editingVariable) {
            handleEdit(
              variable,
              variables.findIndex((v) => v.name === editingVariable.name)
            );
          } else {
            handleAdd(variable);
          }
        }}
        initialData={editingVariable}
      />
    </Box>
  );
};

export default VariableDefinitionsPanel;
