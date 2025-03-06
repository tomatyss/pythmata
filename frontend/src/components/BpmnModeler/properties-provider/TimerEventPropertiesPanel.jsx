import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  FormControl,
  FormHelperText,
  Select,
  MenuItem,
  InputLabel
} from '@mui/material';

/**
 * Timer Event Properties Panel
 * 
 * A component that renders timer-specific properties for timer events
 * 
 * @param {Object} props - Component props
 * @param {Object} props.element - The BPMN element
 * @param {Object} props.modeler - The BPMN modeler instance
 */
const TimerEventPropertiesPanel = ({ element, modeler }) => {
  const [timerType, setTimerType] = useState('duration'); // duration, date, cycle
  const [timerValue, setTimerValue] = useState('');
  
  // Get current timer definition
  useEffect(() => {
    if (!element || !element.businessObject) return;
    
    const businessObject = element.businessObject;
    
    // First check if we have a timer definition in the extension elements
    let timerConfig = null;
    if (businessObject.extensionElements && businessObject.extensionElements.values) {
      timerConfig = businessObject.extensionElements.values.find(
        ext => ext.$type === 'pythmata:TimerEventConfig'
      );
    }
    
    // If we have a timer config in extension elements, use that
    if (timerConfig) {
      setTimerType(timerConfig.timerType || 'duration');
      setTimerValue(timerConfig.timerValue || '');
    } 
    // Otherwise check if element has timer definition in the standard BPMN way
    else if (businessObject.eventDefinitions && 
        businessObject.eventDefinitions.length > 0 &&
        businessObject.eventDefinitions[0].$type === 'bpmn:TimerEventDefinition') {
      
      const timerDef = businessObject.eventDefinitions[0];
      
      // Determine timer type and value
      if (timerDef.timeDuration) {
        setTimerType('duration');
        setTimerValue(timerDef.timeDuration.body || '');
      } else if (timerDef.timeDate) {
        setTimerType('date');
        setTimerValue(timerDef.timeDate.body || '');
      } else if (timerDef.timeCycle) {
        setTimerType('cycle');
        setTimerValue(timerDef.timeCycle.body || '');
      }
    }
  }, [element]);

  // Handle timer type change
  const handleTimerTypeChange = (event) => {
    setTimerType(event.target.value);
    // Reset timer value when changing types
    setTimerValue('');
    updateTimerDefinition(event.target.value, '');
  };

  // Handle timer value change
  const handleTimerValueChange = (event) => {
    const newValue = event.target.value;
    setTimerValue(newValue);
    updateTimerDefinition(timerType, newValue);
  };
  
  // Update timer definition in BPMN XML
  const updateTimerDefinition = (type, value) => {
    if (!modeler || !element) return;
    
    const modeling = modeler.get('modeling');
    const moddle = modeler.get('moddle');
    const businessObject = element.businessObject;
    
    // 1. Update the extension element with our custom timer config
    let extensionElements = businessObject.extensionElements;
    if (!extensionElements) {
      extensionElements = moddle.create('bpmn:ExtensionElements', { values: [] });
    }
    
    // Find existing timer config
    let timerConfig = extensionElements.values.find(
      ext => ext.$type === 'pythmata:TimerEventConfig'
    );
    
    // Create or update timer config
    if (!timerConfig) {
      timerConfig = moddle.create('pythmata:TimerEventConfig', {
        timerType: type,
        timerValue: value
      });
      extensionElements.values.push(timerConfig);
    } else {
      timerConfig.timerType = type;
      timerConfig.timerValue = value;
    }
    
    // 2. Also update the standard BPMN timer definition
    // Create timer event definition if it doesn't exist
    let timerDef = businessObject.eventDefinitions?.[0];
    if (!timerDef || timerDef.$type !== 'bpmn:TimerEventDefinition') {
      timerDef = moddle.create('bpmn:TimerEventDefinition', {});
      businessObject.eventDefinitions = [timerDef];
    }
    
    // Reset all timer properties
    timerDef.timeDate = null;
    timerDef.timeDuration = null;
    timerDef.timeCycle = null;
    
    // Set the appropriate timer property based on type
    if (value) {
      if (type === 'duration') {
        timerDef.timeDuration = moddle.create('bpmn:FormalExpression', { body: value });
      } else if (type === 'date') {
        timerDef.timeDate = moddle.create('bpmn:FormalExpression', { body: value });
      } else if (type === 'cycle') {
        timerDef.timeCycle = moddle.create('bpmn:FormalExpression', { body: value });
      }
    }
    
    // Update the element with both standard and extension properties
    modeling.updateProperties(element, {
      extensionElements: extensionElements,
      eventDefinitions: [timerDef]
    });
  };

  // Helper function to get placeholder text based on timer type
  const getPlaceholder = () => {
    switch (timerType) {
      case 'duration':
        return 'e.g., PT1H30M (1 hour and 30 minutes)';
      case 'date':
        return 'e.g., 2025-03-15T09:00:00';
      case 'cycle':
        return 'e.g., R3/PT1H (repeat 3 times, every hour)';
      default:
        return '';
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        Timer Configuration
      </Typography>
      
      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Timer Type</InputLabel>
        <Select
          value={timerType}
          onChange={handleTimerTypeChange}
          label="Timer Type"
          size="small"
        >
          <MenuItem value="duration">Duration</MenuItem>
          <MenuItem value="date">Date</MenuItem>
          <MenuItem value="cycle">Cycle</MenuItem>
        </Select>
        <FormHelperText>
          {timerType === 'duration' && 'Time period from process start'}
          {timerType === 'date' && 'Specific date and time'}
          {timerType === 'cycle' && 'Repeating time interval'}
        </FormHelperText>
      </FormControl>
      
      <FormControl fullWidth sx={{ mb: 2 }}>
        <TextField
          label="Timer Value"
          value={timerValue}
          onChange={handleTimerValueChange}
          size="small"
          placeholder={getPlaceholder()}
        />
        <FormHelperText>
          {timerType === 'duration' && 'ISO 8601 duration format (PT1H30M)'}
          {timerType === 'date' && 'ISO 8601 date format (YYYY-MM-DDThh:mm:ss)'}
          {timerType === 'cycle' && 'ISO 8601 repeating interval (R3/PT1H)'}
        </FormHelperText>
      </FormControl>
    </Box>
  );
};

export default TimerEventPropertiesPanel;
