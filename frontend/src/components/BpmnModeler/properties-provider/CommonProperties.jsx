import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  FormControl,
  FormHelperText,
} from '@mui/material';

/**
 * Common Properties Panel
 * 
 * A component that renders common properties for all BPMN elements,
 * such as name, documentation, etc.
 * 
 * @param {Object} props - Component props
 * @param {Object} props.element - The BPMN element
 * @param {Object} props.modeler - The BPMN modeler instance
 */
const CommonProperties = ({ element, modeler }) => {
  const [elementName, setElementName] = useState('');
  const [documentation, setDocumentation] = useState('');
  const [elementId, setElementId] = useState('');

  // Get current element properties
  useEffect(() => {
    if (!element || !element.businessObject) return;

    const businessObject = element.businessObject;
    
    // Get name
    setElementName(businessObject.name || '');
    
    // Get element ID
    setElementId(businessObject.id || '');
    
    // Get documentation from extensions
    const extensionElements = businessObject.extensionElements;
    if (extensionElements && extensionElements.values) {
      const elementConfig = extensionElements.values.find(
        ext => ext.$type === 'pythmata:ElementConfig' || 
               ext.$type === 'pythmata:ServiceTaskConfig'
      );
      
      if (elementConfig) {
        setDocumentation(elementConfig.documentation || '');
      }
    }
  }, [element]);

  // Handle name change
  const handleNameChange = (event) => {
    const newName = event.target.value;
    setElementName(newName);
    
    if (!modeler || !element) return;
    
    const modeling = modeler.get('modeling');
    modeling.updateProperties(element, {
      name: newName
    });
  };

  // Handle documentation change
  const handleDocumentationChange = (event) => {
    const newDocumentation = event.target.value;
    setDocumentation(newDocumentation);
    
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
      
      // If found, update documentation
      if (elementConfig) {
        elementConfig.documentation = newDocumentation;
      } else {
        // Create new ServiceTaskConfig
        elementConfig = moddle.create('pythmata:ServiceTaskConfig', {
          documentation: newDocumentation
        });
        extensionElements.values.push(elementConfig);
      }
    } else if (!elementConfig) {
      // Create new ElementConfig for other element types
      elementConfig = moddle.create('pythmata:ElementConfig', {
        documentation: newDocumentation
      });
      extensionElements.values.push(elementConfig);
    } else {
      // Update existing ElementConfig
      elementConfig.documentation = newDocumentation;
    }
    
    // Update the element
    modeling.updateProperties(element, {
      extensionElements: extensionElements
    });
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        General
      </Typography>
      
      <FormControl fullWidth sx={{ mb: 2 }}>
        <TextField
          label="ID"
          value={elementId}
          disabled
          size="small"
        />
        <FormHelperText>Unique identifier (read-only)</FormHelperText>
      </FormControl>
      
      <FormControl fullWidth sx={{ mb: 2 }}>
        <TextField
          label="Name"
          value={elementName}
          onChange={handleNameChange}
          size="small"
        />
        <FormHelperText>Element name</FormHelperText>
      </FormControl>
      
      <FormControl fullWidth sx={{ mb: 2 }}>
        <TextField
          label="Documentation"
          value={documentation}
          onChange={handleDocumentationChange}
          multiline
          rows={3}
          size="small"
        />
        <FormHelperText>Additional documentation for this element</FormHelperText>
      </FormControl>
    </Box>
  );
};

export default CommonProperties;
