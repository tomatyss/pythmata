import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  FormControl,
  FormHelperText,
  Select,
  MenuItem,
  InputLabel,
} from '@mui/material';

/**
 * Gateway Properties Panel
 * 
 * A component that renders properties specific to gateway elements,
 * such as default flow selection.
 * 
 * @param {Object} props - Component props
 * @param {Object} props.element - The BPMN gateway element
 * @param {Object} props.modeler - The BPMN modeler instance
 */
const GatewayPropertiesPanel = ({ element, modeler }) => {
  const [outgoingFlows, setOutgoingFlows] = useState([]);
  const [defaultFlow, setDefaultFlow] = useState('');
  const [gatewayType, setGatewayType] = useState('');

  // Get gateway information when element changes
  useEffect(() => {
    if (!element || !modeler) return;

    try {
      const businessObject = element.businessObject;
      
      // Determine gateway type
      if (element.type === 'bpmn:ExclusiveGateway') {
        setGatewayType('exclusive');
      } else if (element.type === 'bpmn:InclusiveGateway') {
        setGatewayType('inclusive');
      } else if (element.type === 'bpmn:ParallelGateway') {
        setGatewayType('parallel');
      } else {
        setGatewayType('unknown');
      }
      
      // Get outgoing sequence flows
      const elementRegistry = modeler.get('elementRegistry');
      const flows = [];
      
      if (businessObject.outgoing && businessObject.outgoing.length > 0) {
        for (const outgoing of businessObject.outgoing) {
          const flow = elementRegistry.get(outgoing.id);
          if (flow) {
            flows.push({
              id: flow.id,
              businessObject: flow.businessObject,
              name: flow.businessObject.name || flow.id,
            });
          }
        }
      }
      
      setOutgoingFlows(flows);
      
      // Get default flow
      if (businessObject.default) {
        setDefaultFlow(businessObject.default.id);
      } else {
        setDefaultFlow('');
      }
    } catch (error) {
      console.error('Error getting gateway properties:', error);
    }
  }, [element, modeler]);

  // Handle default flow change
  const handleDefaultFlowChange = (event) => {
    const flowId = event.target.value;
    setDefaultFlow(flowId);
    
    if (!modeler || !element) return;
    
    const modeling = modeler.get('modeling');
    
    if (flowId) {
      // Find the flow element
      const elementRegistry = modeler.get('elementRegistry');
      const flowElement = elementRegistry.get(flowId);
      
      if (flowElement) {
        // Set as default flow
        modeling.updateProperties(element, {
          'default': flowElement
        });
      }
    } else {
      // Remove default flow
      modeling.updateProperties(element, {
        'default': null
      });
    }
  };

  // If not a gateway that can have a default flow, don't show default flow selector
  if (gatewayType === 'parallel' || gatewayType === 'unknown') {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          {gatewayType === 'parallel' 
            ? 'Parallel gateways do not use default flows. All outgoing paths are activated simultaneously.' 
            : 'No specific properties available for this gateway type.'}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        Gateway Configuration
      </Typography>
      
      {gatewayType === 'exclusive' && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          For exclusive gateways (XOR), only one outgoing flow will be activated based on the first condition that evaluates to true.
          If no conditions are true, the default flow will be taken.
        </Typography>
      )}
      
      {gatewayType === 'inclusive' && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          For inclusive gateways (OR), all outgoing flows with conditions that evaluate to true will be activated.
          If no conditions are true, the default flow will be taken.
        </Typography>
      )}
      
      <FormControl fullWidth sx={{ mt: 2 }}>
        <InputLabel id="default-flow-label">Default Flow</InputLabel>
        <Select
          labelId="default-flow-label"
          value={defaultFlow}
          onChange={handleDefaultFlowChange}
          label="Default Flow"
        >
          <MenuItem value="">
            <em>None</em>
          </MenuItem>
          {outgoingFlows.map((flow) => (
            <MenuItem key={flow.id} value={flow.id}>
              {flow.name}
            </MenuItem>
          ))}
        </Select>
        <FormHelperText>
          The default flow is taken when no conditions evaluate to true
        </FormHelperText>
      </FormControl>
      
      <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
        To configure conditions on outgoing flows, select each sequence flow and edit its properties.
      </Typography>
    </Box>
  );
};

export default GatewayPropertiesPanel;
