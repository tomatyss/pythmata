import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Grid,
  FormHelperText,
  CircularProgress,
  Divider,
  Button,
  IconButton,
  Alert,
  SelectChangeEvent,
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import apiService from '@/services/api';
import BpmnModeler from 'bpmn-js/lib/Modeler';

// Define types for BPMN elements and properties
interface BusinessObject {
  extensionElements?: {
    values: ExtensionElement[];
  };
}

interface BpmnElement {
  id: string;
  type: string;
  businessObject: BusinessObject;
}

// Define types for the modeler modules
interface ElementRegistry {
  get(id: string): BpmnElement;
}

interface Modeling {
  updateProperties(
    element: BpmnElement,
    properties: Record<string, unknown>
  ): void;
}

interface Moddle {
  create<T>(type: string, properties?: Record<string, unknown>): T;
}

// This interface is used in ProcessDesigner.tsx

interface EventBus {
  on<T = unknown>(event: string, callback: (event: T) => void): void;
}

// Define a mapping of module names to their types
interface ModuleTypeMap {
  elementRegistry: ElementRegistry;
  modeling: Modeling;
  moddle: Moddle;
  eventBus: EventBus;
}

// Define a type for the modeler with the methods we need
type ModelerModule = keyof ModuleTypeMap;

// Export this type for use in tests
export type ExtendedBpmnModeler = BpmnModeler & {
  get<T extends ModelerModule>(name: T): ModuleTypeMap[T];
};

interface ServiceTaskProperty {
  name: string;
  label: string;
  type: string;
  required: boolean;
  default?: unknown;
  options?: string[];
  description?: string;
}

interface ServiceTask {
  name: string;
  description: string;
  properties: ServiceTaskProperty[];
}

interface ServiceTaskPanelProps {
  elementId: string;
  modeler: ExtendedBpmnModeler;
  onClose: () => void;
}

// Define types for extension elements
interface ExtensionElement {
  $type: string;
  taskName?: string;
  properties?: {
    values: PropertyValue[];
  };
}

interface PropertyValue {
  name: string;
  value: string;
}

const ServiceTaskPanel: React.FC<ServiceTaskPanelProps> = ({
  elementId,
  modeler,
  onClose,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [serviceTasks, setServiceTasks] = useState<ServiceTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<string>('');
  const [properties, setProperties] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);

  // Fetch available service tasks
  useEffect(() => {
    const fetchServiceTasks = async () => {
      try {
        setLoading(true);
        const response = await apiService.getServiceTasks();
        console.error('Service tasks response:', response);
        if (response?.data) {
          setServiceTasks(response.data);
          setError(null);
        } else {
          console.error('Invalid service tasks response:', response);
          setError('Invalid service tasks response format');
          setServiceTasks([]);
        }
      } catch (error) {
        console.error('Failed to fetch service tasks:', error);
        setError('Failed to load service tasks. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchServiceTasks();
  }, []);

  // Get current element and its service task configuration
  useEffect(() => {
    if (!modeler || !elementId) return;

    try {
      const elementRegistry = modeler.get('elementRegistry');
      const element = elementRegistry.get(elementId);

      if (!element) {
        setError(`Element with ID ${elementId} not found`);
        return;
      }

      // Extract service task configuration from element extensions
      const businessObject = element.businessObject;
      const extensionElements = businessObject.extensionElements;

      if (extensionElements?.values) {
        const serviceConfig = extensionElements.values.find(
          (ext: ExtensionElement) => ext.$type === 'pythmata:ServiceTaskConfig'
        );

        if (serviceConfig) {
          setSelectedTask(serviceConfig.taskName || '');

          // Parse properties
          const props: Record<string, unknown> = {};
          if (serviceConfig.properties?.values) {
            serviceConfig.properties.values.forEach((prop: PropertyValue) => {
              try {
                props[prop.name] = JSON.parse(prop.value);
              } catch {
                props[prop.name] = prop.value;
              }
            });
          }

          setProperties(props);
        }
      }
    } catch (error) {
      console.error('Error getting element configuration:', error);
      setError('Failed to load service task configuration');
    }
  }, [modeler, elementId]);

  // Handle service task type change
  const handleTaskChange = (event: SelectChangeEvent<string>) => {
    const taskName = event.target.value;
    setSelectedTask(taskName);

    // Reset properties when task changes
    if (serviceTasks && serviceTasks.length > 0) {
      const task = serviceTasks.find((t) => t.name === taskName);
      if (task) {
        const defaultProps: Record<string, unknown> = {};
        task.properties.forEach((prop) => {
          defaultProps[prop.name] = prop.default || '';
        });
        setProperties(defaultProps);
      } else {
        setProperties({});
      }
    } else {
      setProperties({});
    }
  };

  // Handle property change
  const handlePropertyChange = (name: string, value: unknown) => {
    setProperties((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  // Save service task configuration
  const handleSave = () => {
    if (!modeler || !elementId || !selectedTask) {
      setError('Missing required data: modeler, elementId, or selectedTask');
      return;
    }

    try {
      setSaving(true);

      // Check if modeler is properly initialized
      if (typeof modeler.get !== 'function') {
        console.error('Modeler is not properly initialized:', modeler);
        setError('Failed to save: Modeler is not properly initialized');
        setSaving(false);
        return;
      }

      try {
        // Get required components from modeler
        const elementRegistry = modeler.get('elementRegistry');
        if (!elementRegistry) {
          console.error('Element registry not found');
          setError('Failed to save: Element registry not found');
          return;
        }

        const modeling = modeler.get('modeling');
        if (!modeling) {
          console.error('Modeling module not found');
          setError('Failed to save: Modeling module not found');
          return;
        }

        const moddle = modeler.get('moddle');
        if (!moddle) {
          console.error('Moddle module not found');
          setError('Failed to save: Moddle module not found');
          return;
        }

        // Get element
        const element = elementRegistry.get(elementId);
        if (!element) {
          setError(`Element with ID ${elementId} not found`);
          return;
        }

        const businessObject = element.businessObject;
        if (!businessObject) {
          console.error('Business object not found for element:', element);
          setError('Failed to save: Business object not found');
          return;
        }

        // Create extension elements if they don't exist
        let extensionElements = businessObject.extensionElements;
        if (!extensionElements) {
          extensionElements = moddle.create<{
            values: ExtensionElement[];
          }>('bpmn:ExtensionElements', {
            values: [],
          });
        }

        // Remove existing service task config
        if (extensionElements?.values) {
          extensionElements.values = extensionElements.values.filter(
            (ext: ExtensionElement) =>
              ext.$type !== 'pythmata:ServiceTaskConfig'
          );
        } else if (extensionElements) {
          extensionElements.values = [];
        }

        // Create new service task config
        const propertyElements = Object.entries(properties).map(
          ([key, value]) => {
            return moddle.create('pythmata:Property', {
              name: key,
              value:
                typeof value === 'object'
                  ? JSON.stringify(value)
                  : String(value),
            });
          }
        );

        const propertiesElement = moddle.create('pythmata:Properties', {
          values: propertyElements,
        });

        const serviceTaskConfig = moddle.create<ExtensionElement>(
          'pythmata:ServiceTaskConfig',
          {
            taskName: selectedTask,
            properties: propertiesElement,
          }
        );

        if (extensionElements?.values) {
          extensionElements.values.push(serviceTaskConfig);
        }

        // Update the element
        modeling.updateProperties(element, {
          extensionElements: extensionElements,
        });

        onClose();
      } catch (modelError) {
        console.error('Error accessing modeler:', modelError);
        setError(
          'Failed to save service task configuration: Error accessing modeler'
        );
      }
    } catch (error) {
      console.error('Failed to save service task configuration:', error);
      setError('Failed to save service task configuration. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  const selectedTaskDef =
    serviceTasks && serviceTasks.length > 0
      ? serviceTasks.find((t) => t.name === selectedTask)
      : undefined;

  return (
    <Box sx={{ p: 2 }}>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 2,
        }}
      >
        <Typography variant="h6">Service Task Configuration</Typography>
        <IconButton onClick={onClose} aria-label="close">
          <CloseIcon />
        </IconButton>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel id="service-task-type-label">Service Task Type</InputLabel>
        <Select
          labelId="service-task-type-label"
          id="service-task-type"
          value={selectedTask}
          onChange={handleTaskChange}
          label="Service Task Type"
        >
          <MenuItem value="">
            <em>None</em>
          </MenuItem>
          {serviceTasks && serviceTasks.length > 0
            ? serviceTasks.map((task) => (
                <MenuItem key={task.name} value={task.name}>
                  {task.name}
                </MenuItem>
              ))
            : null}
        </Select>
        <FormHelperText>Select the type of service to execute</FormHelperText>
      </FormControl>

      {selectedTaskDef && (
        <>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            {selectedTaskDef.description}
          </Typography>

          <Divider sx={{ my: 2 }} />

          <Grid container spacing={2}>
            {selectedTaskDef.properties.map((prop) => (
              <Grid item xs={12} key={prop.name}>
                {prop.type === 'boolean' ? (
                  <FormControl fullWidth>
                    <InputLabel id={`${prop.name}-label`}>
                      {prop.label || prop.name}
                    </InputLabel>
                    <Select
                      labelId={`${prop.name}-label`}
                      id={prop.name}
                      value={properties[prop.name] || false}
                      onChange={(e) =>
                        handlePropertyChange(prop.name, e.target.value)
                      }
                      label={prop.label || prop.name}
                    >
                      <MenuItem value="true">True</MenuItem>
                      <MenuItem value="false">False</MenuItem>
                    </Select>
                    {prop.description && (
                      <FormHelperText>{prop.description}</FormHelperText>
                    )}
                  </FormControl>
                ) : prop.type === 'json' ? (
                  <TextField
                    label={prop.label || prop.name}
                    fullWidth
                    multiline
                    rows={4}
                    value={
                      typeof properties[prop.name] === 'object'
                        ? JSON.stringify(properties[prop.name], null, 2)
                        : properties[prop.name] || ''
                    }
                    onChange={(e) =>
                      handlePropertyChange(prop.name, e.target.value)
                    }
                    helperText={prop.description}
                  />
                ) : prop.options ? (
                  <FormControl fullWidth>
                    <InputLabel id={`${prop.name}-label`}>
                      {prop.label || prop.name}
                    </InputLabel>
                    <Select
                      labelId={`${prop.name}-label`}
                      id={prop.name}
                      value={properties[prop.name] || ''}
                      onChange={(e) =>
                        handlePropertyChange(prop.name, e.target.value)
                      }
                      label={prop.label || prop.name}
                    >
                      {prop.options.map((option) => (
                        <MenuItem key={option} value={option}>
                          {option}
                        </MenuItem>
                      ))}
                    </Select>
                    {prop.description && (
                      <FormHelperText>{prop.description}</FormHelperText>
                    )}
                  </FormControl>
                ) : (
                  <TextField
                    label={prop.label || prop.name}
                    fullWidth
                    value={properties[prop.name] || ''}
                    onChange={(e) =>
                      handlePropertyChange(prop.name, e.target.value)
                    }
                    helperText={prop.description}
                    type={prop.type === 'number' ? 'number' : 'text'}
                  />
                )}
              </Grid>
            ))}
          </Grid>

          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              onClick={handleSave}
              disabled={saving}
              data-testid="save-service-task"
            >
              {saving ? 'Saving...' : 'Save'}
            </Button>
          </Box>
        </>
      )}
    </Box>
  );
};

export default ServiceTaskPanel;
