import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  CircularProgress,
  FormHelperText,
  Alert,
  Snackbar,
  Button,
} from '@mui/material';
import { Editor } from '@monaco-editor/react';
import { useParams } from 'react-router-dom';
import apiService from '@/services/api';

/**
 * Gets the default script content based on the selected language
 * 
 * @param {string} language - The script language
 * @returns {string} - Default script content
 */
const getDefaultScriptContent = (language) => {
  switch (language) {
    case 'javascript':
      return '// Write your JavaScript script here\n\n// Set result variable\nresult = null;';
    case 'python':
      return '# Write your Python script here\n\n# Set result variable\nresult = None';
    case 'groovy':
      return '// Write your Groovy script here\n\n// Set result variable\nresult = null';
    default:
      return '// Write your script here\n\n// Set result variable\nresult = null;';
  }
};

/**
 * Validates script content based on the selected language
 * 
 * @param {string} content - Script content to validate
 * @param {string} language - Script language
 * @returns {Object} - Validation result with isValid and message
 */
const validateScript = (content, language) => {
  if (!content) {
    return { isValid: true, message: '' };
  }

  try {
    if (language === 'javascript') {
      // Simple syntax check for JavaScript
      new Function(content);
      return { isValid: true, message: '' };
    } else if (language === 'python') {
      // Basic Python syntax validation (very limited)
      // Check for common syntax errors
      const missingColons = content.split('\n')
        .some(line => /^\s*(if|for|while|def|class|with|try|except|finally|else|elif)\s+.*[^:]\s*$/.test(line));
      
      if (missingColons) {
        return { 
          isValid: false, 
          message: 'Python syntax error: Missing colon after statement' 
        };
      }
      
      // More validation could be added here
      return { isValid: true, message: '' };
    }
    
    // For other languages, we can't validate in the browser
    return { isValid: true, message: '' };
  } catch (err) {
    return {
      isValid: false,
      message: `Syntax error: ${err.message}`
    };
  }
};

/**
 * Script Task Properties Panel
 * 
 * A custom properties panel for script tasks that allows configuring
 * script content, language, and other script-related properties.
 * 
 * @param {Object} props - Component props
 * @param {Object} props.element - The BPMN element
 * @param {Object} props.modeler - The BPMN modeler instance
 */
const ScriptTaskPropertiesPanel = ({ element, modeler }) => {
  // Use refs for values that shouldn't trigger re-renders
  const isMountedRef = useRef(true);
  const savingRef = useRef(false);
  const debounceTimerRef = useRef(null);
  
  // State for script properties
  const [scriptContent, setScriptContent] = useState('');
  const [scriptLanguage, setScriptLanguage] = useState('javascript');
  const [resultVariable, setResultVariable] = useState('');
  const [timeoutValue, setTimeoutValue] = useState('30'); // Keep as string to avoid conversion issues
  
  // State for UI feedback
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [validationStatus, setValidationStatus] = useState({ 
    isValid: true, 
    message: '' 
  });
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  // Get the process ID from the URL
  const { id: processId } = useParams();

  // Supported script languages
  const languages = [
    { value: 'javascript', label: 'JavaScript' },
    { value: 'python', label: 'Python' },
    { value: 'groovy', label: 'Groovy' },
  ];

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  /**
   * Update BPMN model with script properties
   */
  const updateBpmnModel = useCallback(() => {
    if (!modeler || !element || !element.businessObject) return;
    
    try {
      const modeling = modeler.get('modeling');
      const moddle = modeler.get('moddle');
      
      if (!modeling || !moddle) return;
      
      // Update standard BPMN properties
      modeling.updateProperties(element, {
        scriptFormat: scriptLanguage,
        resultVariable: resultVariable || undefined,
        script: scriptContent, // Add this line to set the standard BPMN script property
      });
      
      // Handle extension elements
      const businessObject = element.businessObject;
      let extensionElements = businessObject.extensionElements;
      
      if (!extensionElements) {
        extensionElements = moddle.create('bpmn:ExtensionElements', { values: [] });
      }
      
      // Find existing script config
      let scriptConfig = null;
      if (extensionElements.values && Array.isArray(extensionElements.values)) {
        scriptConfig = extensionElements.values.find(
          ext => ext && ext.$type === 'pythmata:ScriptConfig'
        );
      }
      
      // Update or create script config
      if (scriptConfig) {
        scriptConfig.timeout = timeoutValue;
        scriptConfig.language = scriptLanguage;
        scriptConfig.scriptContent = scriptContent;
      } else {
        const newScriptConfig = moddle.create('pythmata:ScriptConfig', {
          timeout: timeoutValue,
          language: scriptLanguage,
          scriptContent: scriptContent
        });
        
        if (extensionElements.values && Array.isArray(extensionElements.values)) {
          extensionElements.values.push(newScriptConfig);
        } else {
          extensionElements.values = [newScriptConfig];
        }
      }
      
      // Update extension elements
      modeling.updateProperties(element, {
        extensionElements: extensionElements,
      });
    } catch (err) {
      console.error('Failed to update BPMN model:', err);
    }
  }, [element, modeler, scriptContent, scriptLanguage, resultVariable, timeoutValue]);

  /**
   * Save script content to backend
   */
  const saveToBackend = useCallback(async () => {
    if (!processId || !element || !element.businessObject || savingRef.current) return;
    
    const nodeId = element.id;
    savingRef.current = true;
    
    try {
      await apiService.updateScript(processId, nodeId, {
        content: scriptContent || '',
        version: 1, // TODO: Handle versioning properly
      });
      
      // Show success message if component is still mounted
      if (isMountedRef.current) {
        setSnackbarMessage('Script saved automatically');
        setSnackbarOpen(true);
      }
    } catch (err) {
      if (!isMountedRef.current) return;
      
      if (err.response && err.response.status === 422) {
        console.error('Validation error saving script:', err);
      } else if (err.response && err.response.status === 404) {
        // Don't show error for 404 during auto-save
        console.info('Script not found in backend, will be created when process is saved');
      } else {
        console.error('Failed to auto-save script content:', err);
        setError('Failed to save script: ' + (err.message || 'Unknown error'));
      }
    } finally {
      savingRef.current = false;
    }
  }, [processId, element, scriptContent]);

  /**
   * Load script content from BPMN model or backend
   */
  useEffect(() => {
    const loadScriptContent = async () => {
      if (!element || !element.businessObject) return;

      try {
        setLoading(true);
        setError(null);

        const nodeId = element.id;
        const businessObject = element.businessObject;
        
        // Extract script language from BPMN model
        setScriptLanguage(businessObject.scriptFormat || 'javascript');
        setResultVariable(businessObject.resultVariable || '');

        // First check if script content is in the standard BPMN script property
        if (businessObject.script) {
          setScriptContent(businessObject.script);
          
          // Still check extensions for timeout
          if (businessObject.extensionElements && businessObject.extensionElements.values) {
            const scriptConfig = businessObject.extensionElements.values.find(
              ext => ext.$type === 'pythmata:ScriptConfig'
            );
            
            if (scriptConfig && scriptConfig.timeout) {
              setTimeoutValue(scriptConfig.timeout);
            }
          }
          
          setLoading(false);
          return;
        }
        
        // If not in standard property, check extension elements
        if (businessObject.extensionElements && businessObject.extensionElements.values) {
          const scriptConfig = businessObject.extensionElements.values.find(
            ext => ext.$type === 'pythmata:ScriptConfig'
          );

          if (scriptConfig) {
            if (scriptConfig.timeout) {
              setTimeoutValue(scriptConfig.timeout);
            }
            
            // Check if script content is stored in the extension
            if (scriptConfig.scriptContent) {
              setScriptContent(scriptConfig.scriptContent);
              setLoading(false);
              return;
            }
          }
        }

        // If we have a process ID, try to fetch from backend
        if (processId) {
          try {
            // Try to fetch existing script from backend
            const response = await apiService.getScript(processId, nodeId);
            if (response && response.data) {
              setScriptContent(response.data.content || '');
            }
          } catch (err) {
            // If script doesn't exist yet, use default values
            if (err.response && err.response.status === 404) {
              setScriptContent(getDefaultScriptContent(businessObject.scriptFormat || 'javascript'));
            } else if (err.response && err.response.status === 422) {
              console.error('Validation error fetching script:', err);
              // Don't show error, just use default content
              setScriptContent(getDefaultScriptContent(businessObject.scriptFormat || 'javascript'));
            } else {
              console.error('Error fetching script:', err);
              setError('Failed to load script content: ' + (err.message || 'Unknown error'));
            }
          }
        } else {
          // No process ID, use default content
          setScriptContent(getDefaultScriptContent(businessObject.scriptFormat || 'javascript'));
        }
      } catch (err) {
        console.error('Failed to load script content:', err);
        setError('Failed to load script content. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadScriptContent();
  }, [element, modeler, processId]);

  /**
   * Auto-save script content to backend if process ID exists
   */
  useEffect(() => {
    // Skip initial render or if no content
    if (loading || !scriptContent || !element || !element.businessObject) return;
    
    // Clear any existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    
    // Debounce the auto-save to avoid too many API calls
    debounceTimerRef.current = setTimeout(() => {
      // First update the BPMN model
      updateBpmnModel();
      
      // Then save to backend
      saveToBackend();
    }, 1000); // 1 second debounce
    
  }, [scriptContent, loading, element, updateBpmnModel, saveToBackend]);

  /**
   * Handle script content change
   */
  const handleEditorChange = useCallback((value) => {
    const newValue = value || '';
    setScriptContent(newValue);

    // Validate the script
    const validation = validateScript(newValue, scriptLanguage);
    setValidationStatus(validation);
  }, [scriptLanguage]);

  /**
   * Handle script language change
   */
  const handleLanguageChange = useCallback((event) => {
    setScriptLanguage(event.target.value);
  }, []);

  /**
   * Handle result variable change
   */
  const handleResultVariableChange = useCallback((event) => {
    setResultVariable(event.target.value);
  }, []);

  /**
   * Handle timeout change
   */
  const handleTimeoutChange = useCallback((event) => {
    // Keep as string to avoid conversion issues with Material-UI TextField
    setTimeoutValue(event.target.value);
  }, []);

  /**
   * Explicitly save script content
   * This function is called when the user clicks the Save button
   */
  const handleSave = useCallback(() => {
    // Cancel any pending auto-save
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    
    // Immediately update the BPMN model
    updateBpmnModel();
    
    // Save to backend
    saveToBackend();
    
    // Show success message
    setSnackbarMessage('Script saved successfully');
    setSnackbarOpen(true);
  }, [updateBpmnModel, saveToBackend]);

  if (loading) {
    return (
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  // Show info message if process ID is not available
  const showProcessIdInfo = !processId;

  return (
    <Box sx={{ p: 2 }}>
      {/* Snackbar for success messages */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert 
          onClose={() => setSnackbarOpen(false)} 
          severity="success"
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>

      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      {showProcessIdInfo && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Script properties are automatically stored in the process model. Save the process to persist scripts to the server.
        </Alert>
      )}

      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel id="script-language-label">Script Language</InputLabel>
        <Select
          labelId="script-language-label"
          id="script-language-select"
          value={scriptLanguage}
          onChange={handleLanguageChange}
          label="Script Language"
        >
          {languages.map((lang) => (
            <MenuItem key={lang.value} value={lang.value}>
              {lang.label}
            </MenuItem>
          ))}
        </Select>
        <FormHelperText>Select the script language</FormHelperText>
      </FormControl>

      <TextField
        label="Result Variable"
        fullWidth
        value={resultVariable}
        onChange={handleResultVariableChange}
        helperText="Variable name to store the script result"
        sx={{ mb: 2 }}
        inputProps={{
          'data-testid': 'result-variable-input'
        }}
      />

      <TextField
        label="Execution Timeout (seconds)"
        fullWidth
        type="number"
        value={timeoutValue}
        onChange={handleTimeoutChange}
        helperText="Maximum execution time in seconds"
        sx={{ mb: 2 }}
        inputProps={{
          'data-testid': 'timeout-input',
          min: 1
        }}
      />

      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Script Content
      </Typography>

      <Box sx={{ border: 1, borderColor: 'divider', mb: 2 }}>
        <Editor
          height="300px"
          language={scriptLanguage === 'groovy' ? 'java' : scriptLanguage}
          value={scriptContent}
          onChange={handleEditorChange}
          options={{
            minimap: { enabled: false },
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            folding: true,
            tabSize: 2,
          }}
        />
      </Box>

      {!validationStatus.isValid && (
        <Typography color="error" variant="body2" sx={{ mb: 2 }}>
          {validationStatus.message}
        </Typography>
      )}

      {savingRef.current && (
        <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
          <CircularProgress size={16} sx={{ mr: 1 }} />
          <Typography variant="body2" color="text.secondary">
            Auto-saving...
          </Typography>
        </Box>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={handleSave}
          disabled={savingRef.current}
        >
          Save Script
        </Button>
      </Box>
    </Box>
  );
};

export default ScriptTaskPropertiesPanel;
