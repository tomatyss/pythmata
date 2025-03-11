import React, { useState, useEffect } from 'react';
import { Box, Tabs, Tab } from '@mui/material';
import CommonProperties from './CommonProperties';
import InputOutputProperties from './InputOutputProperties';
import ServiceTaskPropertiesPanel from './ServiceTaskPropertiesPanel';
import ScriptTaskPropertiesPanel from './ScriptTaskPropertiesPanel';
import TimerEventPropertiesPanel from './TimerEventPropertiesPanel';
import SequenceFlowPropertiesPanel from './SequenceFlowPropertiesPanel';
import GatewayPropertiesPanel from './GatewayPropertiesPanel';

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
  const [isSequenceFlow, setIsSequenceFlow] = useState(false);
  const [isGateway, setIsGateway] = useState(false);
  const [isScriptTask, setIsScriptTask] = useState(false);
  const [processVariables, setProcessVariables] = useState([]);
  
  // Set element type when element changes
  useEffect(() => {
    if (element && element.type) {
      setElementType(element.type);
      
      // Check if element is a sequence flow
      setIsSequenceFlow(element.type === 'bpmn:SequenceFlow');
      
      // Check if element is a gateway
      setIsGateway(
        element.type === 'bpmn:ExclusiveGateway' ||
        element.type === 'bpmn:InclusiveGateway' ||
        element.type === 'bpmn:ParallelGateway' ||
        element.type === 'bpmn:ComplexGateway' ||
        element.type === 'bpmn:EventBasedGateway'
      );
      
      // Check if element is a script task
      setIsScriptTask(element.type === 'bpmn:ScriptTask');
      
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
  
  // Get process variables
  useEffect(() => {
    if (!modeler) return;
    
    try {
      // Try to get process variables from the root element
      const canvas = modeler.get('canvas');
      const rootElement = canvas.getRootElement();
      
      if (rootElement) {
        const elementRegistry = modeler.get('elementRegistry');
        const process = elementRegistry.get(rootElement.id);
        
        if (process && process.businessObject) {
          // Look for variable definitions in extension elements
          const extensionElements = process.businessObject.extensionElements;
          
          if (extensionElements && extensionElements.values) {
            const variableDefinitions = extensionElements.values.find(
              ext => ext.$type === 'pythmata:VariableDefinitions'
            );
            
            if (variableDefinitions && variableDefinitions.variables) {
              setProcessVariables(variableDefinitions.variables);
              return;
            }
          }
        }
      }
      
      // If we couldn't find variables in the process, set empty array
      setProcessVariables([]);
    } catch (error) {
      console.error('Error getting process variables:', error);
      setProcessVariables([]);
    }
  }, [modeler]);
  
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
      {isSequenceFlow ? (
        // For sequence flows, show a simplified panel with condition editor
        <SequenceFlowPropertiesPanel 
          element={element} 
          modeler={modeler} 
          variables={processVariables} 
        />
      ) : (
        // For all other elements, show the regular tabbed panel
        <>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs 
              value={currentTab} 
              onChange={handleTabChange}
              variant="scrollable"
              scrollButtons="auto"
            >
              <Tab label="General" />
              {isServiceTask && <Tab label="Service" />}
              {isScriptTask && <Tab label="Script" />}
              {isGateway && <Tab label="Gateway" />}
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
          
          {/* Script Task Properties Tab */}
          {currentTab === 1 && isScriptTask && (
            <ScriptTaskPropertiesPanel element={element} modeler={modeler} />
          )}
          
          {/* Gateway Properties Tab */}
          {currentTab === (isServiceTask || isScriptTask ? 2 : 1) && isGateway && (
            <GatewayPropertiesPanel element={element} modeler={modeler} />
          )}
          
          {/* Timer Properties Tab */}
          {currentTab === (
            (isServiceTask || isScriptTask) ? (isGateway ? 3 : 2) : (isGateway ? 2 : 1)
          ) && hasTimerDefinition && (
            <TimerEventPropertiesPanel element={element} modeler={modeler} />
          )}
          
          {/* Input/Output Mappings Tab */}
          {currentTab === (
            (isServiceTask || isScriptTask) ? 
              (isGateway ? 
                (hasTimerDefinition ? 4 : 3) : 
                (hasTimerDefinition ? 3 : 2)
              ) : 
              (isGateway ? 
                (hasTimerDefinition ? 3 : 2) : 
                (hasTimerDefinition ? 2 : 1)
              )
          ) && isTask && (
            <InputOutputProperties element={element} modeler={modeler} />
          )}
        </>
      )}
    </Box>
  );
};

export default ElementPropertiesPanel;
