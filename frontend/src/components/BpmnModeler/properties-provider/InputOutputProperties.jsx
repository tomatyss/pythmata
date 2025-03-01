import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  IconButton,
  TextField,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  FormHelperText,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from '@mui/icons-material';

/**
 * Input/Output Properties Panel
 * 
 * A component that renders input and output mappings for task elements.
 * 
 * @param {Object} props - Component props
 * @param {Object} props.element - The BPMN element
 * @param {Object} props.modeler - The BPMN modeler instance
 */
const InputOutputProperties = ({ element, modeler }) => {
  const [inputs, setInputs] = useState([]);
  const [outputs, setOutputs] = useState([]);
  const [openInputDialog, setOpenInputDialog] = useState(false);
  const [openOutputDialog, setOpenOutputDialog] = useState(false);
  const [currentMapping, setCurrentMapping] = useState({ source: '', target: '' });
  const [editIndex, setEditIndex] = useState(-1);
  const [isEditing, setIsEditing] = useState(false);

  // Get current element mappings
  useEffect(() => {
    if (!element || !element.businessObject) return;

    const businessObject = element.businessObject;
    const extensionElements = businessObject.extensionElements;
    
    if (extensionElements && extensionElements.values) {
      // Find element config
      const elementConfig = extensionElements.values.find(
        ext => ext.$type === 'pythmata:ElementConfig' || 
               ext.$type === 'pythmata:ServiceTaskConfig'
      );
      
      if (elementConfig) {
        // Parse inputs
        const inputMappings = [];
        if (elementConfig.inputs && elementConfig.inputs.values) {
          elementConfig.inputs.values.forEach(prop => {
            try {
              const source = prop.name;
              const target = prop.value;
              inputMappings.push({ source, target });
            } catch (e) {
              console.error('Failed to parse input mapping:', e);
            }
          });
        }
        setInputs(inputMappings);
        
        // Parse outputs
        const outputMappings = [];
        if (elementConfig.outputs && elementConfig.outputs.values) {
          elementConfig.outputs.values.forEach(prop => {
            try {
              const source = prop.name;
              const target = prop.value;
              outputMappings.push({ source, target });
            } catch (e) {
              console.error('Failed to parse output mapping:', e);
            }
          });
        }
        setOutputs(outputMappings);
      }
    }
  }, [element]);

  // Update element extensions with new mappings
  const updateElementExtensions = (newInputs, newOutputs) => {
    if (!modeler || !element) return;
    
    const modeling = modeler.get('modeling');
    const moddle = modeler.get('moddle');
    const businessObject = element.businessObject;
    
    // Create extension elements if they don't exist
    let extensionElements = businessObject.extensionElements;
    if (!extensionElements) {
      extensionElements = moddle.create('bpmn:ExtensionElements', { values: [] });
    }
    
    // Find existing element config
    let elementConfig = extensionElements.values.find(
      ext => ext.$type === 'pythmata:ElementConfig'
    );
    
    // For service tasks, find ServiceTaskConfig instead
    if (!elementConfig && element.type === 'bpmn:ServiceTask') {
      elementConfig = extensionElements.values.find(
        ext => ext.$type === 'pythmata:ServiceTaskConfig'
      );
      
      if (!elementConfig) {
        // Create new ServiceTaskConfig
        elementConfig = moddle.create('pythmata:ServiceTaskConfig', {});
        extensionElements.values.push(elementConfig);
      }
    } else if (!elementConfig) {
      // Create new ElementConfig for other element types
      elementConfig = moddle.create('pythmata:ElementConfig', {});
      extensionElements.values.push(elementConfig);
    }
    
    // Create input mappings
    const inputElements = newInputs.map(input => {
      return moddle.create('pythmata:Property', {
        name: input.source,
        value: input.target,
      });
    });
    
    const inputsElement = moddle.create('pythmata:Properties', {
      values: inputElements,
    });
    
    // Create output mappings
    const outputElements = newOutputs.map(output => {
      return moddle.create('pythmata:Property', {
        name: output.source,
        value: output.target,
      });
    });
    
    const outputsElement = moddle.create('pythmata:Properties', {
      values: outputElements,
    });
    
    // Update element config
    elementConfig.inputs = inputsElement;
    elementConfig.outputs = outputsElement;
    
    // Update the element
    modeling.updateProperties(element, {
      extensionElements: extensionElements,
    });
  };

  // Handle input dialog open
  const handleOpenInputDialog = (index = -1) => {
    if (index >= 0) {
      setCurrentMapping(inputs[index]);
      setEditIndex(index);
      setIsEditing(true);
    } else {
      setCurrentMapping({ source: '', target: '' });
      setIsEditing(false);
    }
    setOpenInputDialog(true);
  };

  // Handle output dialog open
  const handleOpenOutputDialog = (index = -1) => {
    if (index >= 0) {
      setCurrentMapping(outputs[index]);
      setEditIndex(index);
      setIsEditing(true);
    } else {
      setCurrentMapping({ source: '', target: '' });
      setIsEditing(false);
    }
    setOpenOutputDialog(true);
  };

  // Handle dialog close
  const handleCloseDialog = () => {
    setOpenInputDialog(false);
    setOpenOutputDialog(false);
    setCurrentMapping({ source: '', target: '' });
    setEditIndex(-1);
    setIsEditing(false);
  };

  // Handle save input mapping
  const handleSaveInputMapping = () => {
    const newInputs = [...inputs];
    
    if (isEditing && editIndex >= 0) {
      newInputs[editIndex] = currentMapping;
    } else {
      newInputs.push(currentMapping);
    }
    
    setInputs(newInputs);
    updateElementExtensions(newInputs, outputs);
    handleCloseDialog();
  };

  // Handle save output mapping
  const handleSaveOutputMapping = () => {
    const newOutputs = [...outputs];
    
    if (isEditing && editIndex >= 0) {
      newOutputs[editIndex] = currentMapping;
    } else {
      newOutputs.push(currentMapping);
    }
    
    setOutputs(newOutputs);
    updateElementExtensions(inputs, newOutputs);
    handleCloseDialog();
  };

  // Handle delete input mapping
  const handleDeleteInputMapping = (index) => {
    const newInputs = [...inputs];
    newInputs.splice(index, 1);
    setInputs(newInputs);
    updateElementExtensions(newInputs, outputs);
  };

  // Handle delete output mapping
  const handleDeleteOutputMapping = (index) => {
    const newOutputs = [...outputs];
    newOutputs.splice(index, 1);
    setOutputs(newOutputs);
    updateElementExtensions(inputs, newOutputs);
  };

  // Handle mapping field change
  const handleMappingChange = (field, value) => {
    setCurrentMapping(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        Input/Output Mappings
      </Typography>
      
      {/* Input Mappings */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle2">Input Mappings</Typography>
          <Button
            startIcon={<AddIcon />}
            size="small"
            onClick={() => handleOpenInputDialog()}
          >
            Add Input
          </Button>
        </Box>
        
        {inputs.length > 0 ? (
          <List dense>
            {inputs.map((input, index) => (
              <ListItem key={index} divider={index < inputs.length - 1}>
                <ListItemText
                  primary={`${input.source} → ${input.target}`}
                  secondary="Process variable to task input"
                />
                <ListItemSecondaryAction>
                  <IconButton edge="end" onClick={() => handleOpenInputDialog(index)} size="small">
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton edge="end" onClick={() => handleDeleteInputMapping(index)} size="small">
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography variant="body2" color="textSecondary">
            No input mappings defined
          </Typography>
        )}
      </Box>
      
      <Divider sx={{ my: 2 }} />
      
      {/* Output Mappings */}
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle2">Output Mappings</Typography>
          <Button
            startIcon={<AddIcon />}
            size="small"
            onClick={() => handleOpenOutputDialog()}
          >
            Add Output
          </Button>
        </Box>
        
        {outputs.length > 0 ? (
          <List dense>
            {outputs.map((output, index) => (
              <ListItem key={index} divider={index < outputs.length - 1}>
                <ListItemText
                  primary={`${output.source} → ${output.target}`}
                  secondary="Task result to process variable"
                />
                <ListItemSecondaryAction>
                  <IconButton edge="end" onClick={() => handleOpenOutputDialog(index)} size="small">
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton edge="end" onClick={() => handleDeleteOutputMapping(index)} size="small">
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography variant="body2" color="textSecondary">
            No output mappings defined
          </Typography>
        )}
      </Box>
      
      {/* Input Mapping Dialog */}
      <Dialog open={openInputDialog} onClose={handleCloseDialog}>
        <DialogTitle>{isEditing ? 'Edit Input Mapping' : 'Add Input Mapping'}</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <TextField
                  label="Process Variable"
                  value={currentMapping.source}
                  onChange={(e) => handleMappingChange('source', e.target.value)}
                  size="small"
                />
                <FormHelperText>Source process variable name</FormHelperText>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <TextField
                  label="Task Input"
                  value={currentMapping.target}
                  onChange={(e) => handleMappingChange('target', e.target.value)}
                  size="small"
                />
                <FormHelperText>Target task input parameter</FormHelperText>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button 
            onClick={handleSaveInputMapping}
            disabled={!currentMapping.source || !currentMapping.target}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Output Mapping Dialog */}
      <Dialog open={openOutputDialog} onClose={handleCloseDialog}>
        <DialogTitle>{isEditing ? 'Edit Output Mapping' : 'Add Output Mapping'}</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <TextField
                  label="Task Result"
                  value={currentMapping.source}
                  onChange={(e) => handleMappingChange('source', e.target.value)}
                  size="small"
                />
                <FormHelperText>Source task result path (e.g., result.data)</FormHelperText>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <TextField
                  label="Process Variable"
                  value={currentMapping.target}
                  onChange={(e) => handleMappingChange('target', e.target.value)}
                  size="small"
                />
                <FormHelperText>Target process variable name</FormHelperText>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button 
            onClick={handleSaveOutputMapping}
            disabled={!currentMapping.source || !currentMapping.target}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default InputOutputProperties;
