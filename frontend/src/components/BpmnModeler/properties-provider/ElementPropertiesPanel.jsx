import React, { useState, useEffect } from 'react';
import { Box, Tabs, Tab } from '@mui/material';
import CommonProperties from './CommonProperties';
import InputOutputProperties from './InputOutputProperties';
import ServiceTaskPropertiesPanel from './ServiceTaskPropertiesPanel';
import TimerEventPropertiesPanel from './TimerEventPropertiesPanel';

/**
 * Element Properties Panel
 * 
 * A generalized properties panel for all BPMN elements that provides
 * common properties, element-specific properties, and input/output mappings.
 * 
 * @param {Object} props - Component props
 * @param {Object} props.element - The BPMN element
 * @param {Object} props.modeler - The BPMN modeler instance
 */
const ElementPropertiesPanel = ({ element, modeler }) => {
  const [currentTab, setCurrentTab] = useState(0);
  const [elementType, setElementType] = useState('');
  const [hasTimerDefinition, setHasTimerDefinition] = useState(false);
  
  // Set element type when element changes
  useEffect(() => {
    if (element && element.type) {
      setElementType(element.type);
      
      // Check if element has timer definition or is a type that can have timer definitions
      const businessObject = element.businessObject;
      const isTimerEvent = 
        businessObject.eventDefinitions?.some(def => def.$type === 'bpmn:TimerEventDefinition') ||
        element.type.includes('bpmn:TimerEvent');
      
      // Check if element is a type that can have timer definitions
      const canHaveTimer = 
        element.type === 'bpmn:StartEvent' ||
        element.type === 'bpmn:IntermediateCatchEvent' ||
        element.type === 'bpmn:BoundaryEvent';
      
      setHasTimerDefinition(isTimerEvent || canHaveTimer);
    }
  }, [element]);
  
  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };
  
  // Check if element is a task
  const isTask = elementType.includes('Task');
  
  // Check if element is a service task
  const isServiceTask = elementType === 'bpmn:ServiceTask';
  
  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs 
          value={currentTab} 
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="General" />
          {isServiceTask && <Tab label="Service" />}
          {hasTimerDefinition && <Tab label="Timer" />}
          {isTask && <Tab label="I/O Mapping" />}
        </Tabs>
      </Box>
      
      {/* General Properties Tab */}
      {currentTab === 0 && (
        <CommonProperties element={element} modeler={modeler} />
      )}
      
      {/* Service Task Properties Tab */}
      {currentTab === 1 && isServiceTask && (
        <ServiceTaskPropertiesPanel element={element} modeler={modeler} />
      )}
      
      {/* Timer Properties Tab */}
      {currentTab === (isServiceTask ? 2 : 1) && hasTimerDefinition && (
        <TimerEventPropertiesPanel element={element} modeler={modeler} />
      )}
      
      {/* Input/Output Mappings Tab */}
      {currentTab === (isServiceTask ? (hasTimerDefinition ? 3 : 2) : (hasTimerDefinition ? 2 : 1)) && isTask && (
        <InputOutputProperties element={element} modeler={modeler} />
      )}
    </Box>
  );
};

export default ElementPropertiesPanel;
