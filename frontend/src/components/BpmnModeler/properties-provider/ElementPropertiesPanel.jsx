import React, { useState, useEffect } from 'react';
import { Box, Tabs, Tab } from '@mui/material';
import CommonProperties from './CommonProperties';
import InputOutputProperties from './InputOutputProperties';
import ServiceTaskPropertiesPanel from './ServiceTaskPropertiesPanel';

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
  
  // Set element type when element changes
  useEffect(() => {
    if (element && element.type) {
      setElementType(element.type);
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
      
      {/* Input/Output Mappings Tab */}
      {currentTab === (isServiceTask ? 2 : 1) && isTask && (
        <InputOutputProperties element={element} modeler={modeler} />
      )}
    </Box>
  );
};

export default ElementPropertiesPanel;
