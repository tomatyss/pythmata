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
} from '@mui/material';
import apiService from '@/services/api';

/**
 * Service Task Properties Panel
 * 
 * A custom properties panel for service tasks that allows configuring
 * the service task type and its properties.
 * 
 * @param {Object} props - Component props
 * @param {Object} props.element - The BPMN element
 * @param {Object} props.modeler - The BPMN modeler instance
 */
const ServiceTaskPropertiesPanel = ({ element, modeler }) => {
  const [serviceTasks, setServiceTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState('');
  const [properties, setProperties] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch available service tasks
  useEffect(() => {
    const fetchServiceTasks = async () => {
      try {
        setLoading(true);
        const response = await apiService.getServiceTasks();
        setServiceTasks(response.data);
        setError(null);
      } catch (error) {
        console.error('Failed to fetch service tasks:', error);
        setError('Failed to load service tasks. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchServiceTasks();
  }, []);

  // Get current service task configuration from element
  useEffect(() => {
    if (!element || !element.businessObject) return;

    // Extract service task configuration from element extensions
    const businessObject = element.businessObject;
    const extensionElements = businessObject.extensionElements;
    
    if (extensionElements && extensionElements.values) {
      const serviceConfig = extensionElements.values.find(
        ext => ext.$type === 'pythmata:ServiceTaskConfig'
      );
      
      if (serviceConfig) {
        setSelectedTask(serviceConfig.taskName || '');
        
        // Parse properties
        const props = {};
        if (serviceConfig.properties && serviceConfig.properties.values) {
          serviceConfig.properties.values.forEach(prop => {
            try {
              props[prop.name] = JSON.parse(prop.value);
            } catch (e) {
              props[prop.name] = prop.value;
            }
          });
        }
        
        setProperties(props);
      }
    }
  }, [element]);

  // Handle service task type change
  const handleTaskChange = (event) => {
    const taskName = event.target.value;
    setSelectedTask(taskName);
    
    // Reset properties when task changes
    const task = serviceTasks.find(t => t.name === taskName);
    if (task) {
      const defaultProps = {};
      task.properties.forEach(prop => {
        defaultProps[prop.name] = prop.defaultValue || '';
      });
      setProperties(defaultProps);
    } else {
      setProperties({});
    }
    
    // Update BPMN element
    updateElementExtensions(taskName, {});
  };

  // Handle property change
  const handlePropertyChange = (name, value) => {
    setProperties(prev => ({
      ...prev,
      [name]: value,
    }));
    
    // Update BPMN element
    updateElementExtensions(selectedTask, {
      ...properties,
      [name]: value,
    });
  };

  // Update element extensions
  const updateElementExtensions = (taskName, props) => {
    if (!modeler || !element) return;
    
    const modeling = modeler.get('modeling');
    const moddle = modeler.get('moddle');
    const businessObject = element.businessObject;
    
    // Create extension elements if they don't exist
    let extensionElements = businessObject.extensionElements;
    if (!extensionElements) {
      extensionElements = moddle.create('bpmn:ExtensionElements', { values: [] });
    }
    
    // Find existing service task config
    let serviceTaskConfig = extensionElements.values.find(
      ext => ext.$type === 'pythmata:ServiceTaskConfig'
    );
    
    // Get existing values to preserve
    let documentation = '';
    let inputs = null;
    let outputs = null;
    
    if (serviceTaskConfig) {
      // Preserve existing values
      documentation = serviceTaskConfig.documentation || '';
      
      // Preserve input mappings
      inputs = serviceTaskConfig.inputs;
      
      // Preserve output mappings
      outputs = serviceTaskConfig.outputs;
      
      // Remove existing service task config
      extensionElements.values = extensionElements.values.filter(
        ext => ext.$type !== 'pythmata:ServiceTaskConfig'
      );
    }
    
    // Create new service task config
    const propertyElements = Object.entries(props).map(([key, value]) => {
      return moddle.create('pythmata:Property', {
        name: key,
        value: typeof value === 'object' ? JSON.stringify(value) : String(value),
      });
    });
    
    const propertiesElement = moddle.create('pythmata:Properties', {
      values: propertyElements,
    });
    
    // Create empty inputs/outputs if they don't exist
    if (!inputs) {
      inputs = moddle.create('pythmata:Properties', {
        values: [],
      });
    }
    
    if (!outputs) {
      outputs = moddle.create('pythmata:Properties', {
        values: [],
      });
    }
    
    // Create new service task config with preserved values
    serviceTaskConfig = moddle.create('pythmata:ServiceTaskConfig', {
      taskName: taskName,
      properties: propertiesElement,
      documentation: documentation,
      inputs: inputs,
      outputs: outputs
    });
    
    extensionElements.values.push(serviceTaskConfig);
    
    // Update the element
    modeling.updateProperties(element, {
      extensionElements: extensionElements,
    });
  };

  if (loading) {
    return (
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  const selectedTaskDef = serviceTasks.find(t => t.name === selectedTask);

  return (
    <Box sx={{ p: 2 }}>
      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Service Task Type</InputLabel>
        <Select
          value={selectedTask}
          onChange={handleTaskChange}
          label="Service Task Type"
        >
          <MenuItem value="">
            <em>None</em>
          </MenuItem>
          {serviceTasks.map((task) => (
            <MenuItem key={task.name} value={task.name}>
              {task.name}
            </MenuItem>
          ))}
        </Select>
        <FormHelperText>Select the type of service to execute</FormHelperText>
      </FormControl>
      
      {selectedTaskDef && (
        <>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            {selectedTaskDef.description}
          </Typography>
          
          <Grid container spacing={2}>
            {selectedTaskDef.properties.map((prop) => (
              <Grid item xs={12} key={prop.name}>
                {prop.type === 'boolean' ? (
                  <FormControl fullWidth>
                    <InputLabel>{prop.label || prop.name}</InputLabel>
                    <Select
                      value={properties[prop.name] || false}
                      onChange={(e) => handlePropertyChange(prop.name, e.target.value)}
                      label={prop.label || prop.name}
                    >
                      <MenuItem value={true}>True</MenuItem>
                      <MenuItem value={false}>False</MenuItem>
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
                    onChange={(e) => handlePropertyChange(prop.name, e.target.value)}
                    helperText={prop.description}
                  />
                ) : prop.options ? (
                  <FormControl fullWidth>
                    <InputLabel>{prop.label || prop.name}</InputLabel>
                    <Select
                      value={properties[prop.name] || ''}
                      onChange={(e) => handlePropertyChange(prop.name, e.target.value)}
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
                    onChange={(e) => handlePropertyChange(prop.name, e.target.value)}
                    helperText={prop.description}
                    type={prop.type === 'number' ? 'number' : 'text'}
                  />
                )}
              </Grid>
            ))}
          </Grid>
        </>
      )}
    </Box>
  );
};

export default ServiceTaskPropertiesPanel;
