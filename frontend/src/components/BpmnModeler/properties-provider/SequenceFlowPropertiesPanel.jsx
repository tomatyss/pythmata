import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  FormControl,
  FormHelperText,
  Checkbox,
  FormControlLabel,
  Alert,
  Chip,
} from '@mui/material';

/**
 * Sequence Flow Properties Panel
 * 
 * A component that renders properties for sequence flows, including
 * condition expressions for flows connected to gateways.
 * 
 * @param {Object} props - Component props
 * @param {Object} props.element - The BPMN sequence flow element
 * @param {Object} props.modeler - The BPMN modeler instance
 * @param {Array} props.variables - Available process variables
 */
const SequenceFlowPropertiesPanel = ({ element, modeler, variables = [] }) => {
  const [conditionExpression, setConditionExpression] = useState('');
  const [isDefaultFlow, setIsDefaultFlow] = useState(false);
  const [sourceElement, setSourceElement] = useState(null);
  const [validationError, setValidationError] = useState(null);
  const [isFromGateway, setIsFromGateway] = useState(false);
  const [gatewayType, setGatewayType] = useState(null);

  // Get source element and check if it's a gateway
  useEffect(() => {
    if (!element || !modeler) return;

    try {
      const elementRegistry = modeler.get('elementRegistry');
      const businessObject = element.businessObject;
      const sourceRef = businessObject.sourceRef;

      if (sourceRef) {
        const source = elementRegistry.get(sourceRef.id);
        setSourceElement(source);

        // Check if source is a gateway
        const isGateway = source && source.type.includes('Gateway');
        setIsFromGateway(isGateway);

        // Determine gateway type
        if (isGateway) {
          if (source.type === 'bpmn:ExclusiveGateway') {
            setGatewayType('exclusive');
          } else if (source.type === 'bpmn:InclusiveGateway') {
            setGatewayType('inclusive');
          } else if (source.type === 'bpmn:ParallelGateway') {
            setGatewayType('parallel');
          }
        }

        // Check if this is a default flow
        if (isGateway && sourceRef.default && sourceRef.default.id === businessObject.id) {
          setIsDefaultFlow(true);
        } else {
          setIsDefaultFlow(false);
        }
      }

      // Get condition expression
      if (businessObject.conditionExpression) {
        setConditionExpression(businessObject.conditionExpression.body || '');
      } else {
        setConditionExpression('');
      }
    } catch (error) {
      console.error('Error getting sequence flow properties:', error);
    }
  }, [element, modeler]);

  // Handle condition expression change
  const handleConditionChange = (event) => {
    const newCondition = event.target.value;
    setConditionExpression(newCondition);

    // Validate expression
    validateExpression(newCondition);
  };

  // Handle default flow change
  const handleDefaultFlowChange = (event) => {
    const checked = event.target.checked;
    setIsDefaultFlow(checked);

    if (!modeler || !sourceElement) return;

    const modeling = modeler.get('modeling');

    if (checked) {
      // Set as default flow
      modeling.updateProperties(sourceElement, {
        'default': element
      });

      // Clear condition expression
      updateConditionExpression('');
    } else {
      // Remove default flow
      modeling.updateProperties(sourceElement, {
        'default': null
      });
    }
  };

  // Update condition expression in the BPMN model
  const updateConditionExpression = (expression) => {
    if (!modeler || !element) return;

    const modeling = modeler.get('modeling');
    const moddle = modeler.get('moddle');

    if (!expression) {
      // Remove condition expression
      modeling.updateProperties(element, {
        conditionExpression: null
      });
      setConditionExpression('');
    } else {
      // Create condition expression
      const conditionExpression = moddle.create('bpmn:FormalExpression', {
        body: expression,
        language: 'javascript'
      });

      // Update the element
      modeling.updateProperties(element, {
        conditionExpression: conditionExpression
      });
    }
  };

  // Validate expression
  const validateExpression = (expression) => {
    if (!expression) {
      setValidationError(null);
      return true;
    }

    // Check if expression is wrapped in ${...}
    if (!expression.startsWith('${') || !expression.endsWith('}')) {
      setValidationError("Expression must be wrapped in '${...}'");
      return false;
    }

    // Extract the actual expression
    const actualExpression = expression.substring(2, expression.length - 1).trim();

    // Check for empty expression
    if (!actualExpression) {
      setValidationError('Expression cannot be empty');
      return false;
    }

    // Check for Java/JUEL-style methods that aren't valid in JavaScript
    if (actualExpression.includes('.size()')) {
      // This is likely a Java/JUEL expression using .size() method
      // We'll do a basic check to see if the variable exists
      const variableName = actualExpression.split('.')[0].trim();
      
      // Check if the variable is defined
      const variableExists = variables.some(v => v.name === variableName);
      if (!variableExists) {
        setValidationError(`Variable '${variableName}' is not defined. Define it in Process Settings.`);
        return false;
      }
      
      // For Java/JUEL expressions, we'll skip the JavaScript validation
      setValidationError(null);
      return true;
    }

    // Basic syntax check for JavaScript expressions
    try {
      // Create a mock context with all the variables to prevent "Can't find variable" errors
      const mockVariables = {};
      variables.forEach(variable => {
        // Add each variable as a property with a dummy value based on its type
        mockVariables[variable.name] = variable.type === 'number' ? 0 : [];
      });
      
      // Add common collection methods to mock variables
      Object.keys(mockVariables).forEach(key => {
        if (Array.isArray(mockVariables[key])) {
          // Add a size() method that returns length for Java compatibility
          mockVariables[key].size = function() { return this.length; };
        }
      });
      
      // Extract variable names from the expression
      const variablePattern = /\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?!\s*\()/g;
      const matches = actualExpression.match(variablePattern) || [];
      const uniqueVars = [...new Set(matches)];
      
      // Check if all variables in the expression are defined
      const undefinedVars = uniqueVars.filter(v => !mockVariables[v] && !['true', 'false', 'null'].includes(v));
      if (undefinedVars.length > 0) {
        setValidationError(`Variable '${undefinedVars[0]}' is not defined. Define it in Process Settings.`);
        return false;
      }
      
      // Create a function that evaluates the expression with the mock variables
      const variableNames = Object.keys(mockVariables);
      
      // Convert Java/JUEL-style expressions to JavaScript
      let jsExpression = actualExpression;
      // Replace .size() with .length for arrays
      jsExpression = jsExpression.replace(/\.size\(\)/g, '.length');
      
      // Pass the variables as arguments to the function
      new Function(...variableNames, `return (${jsExpression})`);
      
      setValidationError(null);
      return true;
    } catch (e) {
      // Provide more helpful error messages
      if (e.message.includes("Can't find variable")) {
        const varName = e.message.split("Can't find variable:")[1]?.trim() || 'Unknown';
        setValidationError(`Variable '${varName}' is not defined. Define it in Process Settings.`);
      } else {
        setValidationError(`Syntax error: ${e.message}`);
      }
      return false;
    }
  };

  // Apply condition expression to the model
  const applyConditionExpression = () => {
    if (validateExpression(conditionExpression)) {
      updateConditionExpression(conditionExpression);
    }
  };

  // Insert variable into expression
  const insertVariable = (variableName) => {
    // If expression is empty, create a new one with the variable
    if (!conditionExpression) {
      const newExpression = "${" + variableName + "}";
      setConditionExpression(newExpression);
      updateConditionExpression(newExpression);
      return;
    }
    
    // If expression doesn't have ${} wrapper, add it
    if (!conditionExpression.startsWith('${') || !conditionExpression.endsWith('}')) {
      const newExpression = "${" + variableName + "}";
      setConditionExpression(newExpression);
      updateConditionExpression(newExpression);
      return;
    }
    
    // Insert variable at cursor position or append to expression
    const expressionContent = conditionExpression.substring(2, conditionExpression.length - 1);
    const newExpression = "${" + expressionContent + " " + variableName + "}";
    setConditionExpression(newExpression);
    updateConditionExpression(newExpression);
  };

  // If source is not a gateway, don't show condition editor
  if (!isFromGateway) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Conditions can only be set on sequence flows from gateways.
        </Typography>
      </Box>
    );
  }

  // If source is a parallel gateway, show message
  if (gatewayType === 'parallel') {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Parallel gateways do not use conditions. All outgoing flows are activated simultaneously.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        Flow Condition
      </Typography>

      {gatewayType === 'exclusive' && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          For exclusive gateways (XOR), only one outgoing flow will be activated based on the first condition that evaluates to true.
        </Typography>
      )}

      {gatewayType === 'inclusive' && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          For inclusive gateways (OR), all outgoing flows with conditions that evaluate to true will be activated.
        </Typography>
      )}

      <FormControlLabel
        control={
          <Checkbox
            checked={isDefaultFlow}
            onChange={handleDefaultFlowChange}
          />
        }
        label="Use as default flow (taken when no conditions are true)"
        sx={{ mb: 2 }}
      />

      {!isDefaultFlow && (
        <>
          <FormControl fullWidth sx={{ mb: 2 }} error={!!validationError}>
            <TextField
              label="Condition Expression"
              value={conditionExpression}
              onChange={handleConditionChange}
              onBlur={applyConditionExpression}
              multiline
              rows={2}
              size="small"
              placeholder="Example: ${variable > value}"
            />
            <FormHelperText>
              Use dollar sign with curly braces format, e.g. '${positions.length > 0}' or '${positions.size() > 0}'
            </FormHelperText>
            {validationError && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {validationError}
              </Alert>
            )}
          </FormControl>

          <Typography variant="caption" sx={{ display: 'block', mb: 1 }}>
            Available Variables:
          </Typography>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
            {variables.map(variable => (
              <Chip
                key={variable.name}
                label={variable.name}
                size="small"
                onClick={() => insertVariable(variable.name)}
                sx={{ mb: 0.5 }}
              />
            ))}
            {variables.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                No variables defined. Define process variables in the Process Settings.
              </Typography>
            )}
          </Box>

          <Typography variant="caption" sx={{ display: 'block', mb: 1 }}>
            Common Operators:
          </Typography>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {['==', '!=', '>', '>=', '<', '<=', '&&', '||', '!'].map(op => (
              <Chip
                key={op}
                label={op}
                size="small"
                onClick={() => {
                  let newExpression;
                  if (conditionExpression) {
                    // Extract content from ${...}
                    const content = conditionExpression.startsWith('${') && conditionExpression.endsWith('}')
                      ? conditionExpression.substring(2, conditionExpression.length - 1)
                      : conditionExpression;
                    // Create new expression with operator
                    newExpression = "${" + content + " " + op + "}";
                  } else {
                    newExpression = "${" + op + "}";
                  }
                  setConditionExpression(newExpression);
                  updateConditionExpression(newExpression);
                }}
                sx={{ mb: 0.5 }}
              />
            ))}
          </Box>
        </>
      )}
    </Box>
  );
};

export default SequenceFlowPropertiesPanel;
