import { useEffect, useRef, useState, useCallback } from 'react';
import { Snackbar, Alert } from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import apiService from '@/services/api';
import {
  Box,
  Paper,
  AppBar,
  Toolbar,
  Button,
  TextField,
  CircularProgress,
  Typography,
  Drawer,
  IconButton,
  Tabs,
  Tab,
} from '@mui/material';
import MonacoEditor from '@monaco-editor/react';
import {
  Save as SaveIcon,
  Settings as SettingsIcon,
  ContentCopy as ContentCopyIcon,
  Chat as ChatIcon,
} from '@mui/icons-material';
import BpmnModeler from 'bpmn-js/lib/Modeler';
import DmnModeler from 'dmn-js/lib/Modeler';

// Import components
import ChatPanel from '@/components/shared/ChatPanel';
import VariableDefinitionsPanel from '@/components/shared/VariableDefinitionsPanel/VariableDefinitionsPanel';
import ElementPanel from '@/components/shared/ElementPanel';

// Import types
import { ProcessVariableDefinition } from '@/types/process';
import { convertDefinitionsToBackend } from '@/utils/variableTypeConverter';

// Import styles
import 'bpmn-js/dist/assets/diagram-js.css';
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css';
import '@/components/BpmnModeler/PaletteLeft.css';
import '@/components/BpmnModeler/PropertiesPanelOverlay.css';
// Import DMN-JS styles
import 'dmn-js/dist/assets/diagram-js.css';
import 'dmn-js/dist/assets/dmn-js-shared.css';
import 'dmn-js/dist/assets/dmn-js-drd.css';
import 'dmn-js/dist/assets/dmn-js-decision-table.css';
import 'dmn-js/dist/assets/dmn-js-literal-expression.css';
import 'dmn-js/dist/assets/dmn-font/css/dmn.css';

// Import pythmata moddle extension for service tasks
import pythmataModdleDescriptor from '@/components/BpmnModeler/moddle/pythmata.json';

// Import types
import * as BpmnTypes from './types';
import * as DmnTypes from './dmn.types';

// Define validation rule interface
interface ValidationRule {
  validate(modeler: BpmnTypes.ExtendedBpmnModeler): string[];
}

// Start event validation rule
const startEventRule: ValidationRule = {
  validate(modeler: BpmnTypes.ExtendedBpmnModeler): string[] {
    const elementRegistry = modeler.get('elementRegistry');
    const startEvents = elementRegistry.filter(
      (el: BpmnTypes.BpmnElement) => el.type === 'bpmn:StartEvent'
    );
    return startEvents.length > 0
      ? []
      : ['Process must have at least one start event'];
  },
};

// End event validation rule
const endEventRule: ValidationRule = {
  validate(modeler: BpmnTypes.ExtendedBpmnModeler): string[] {
    const elementRegistry = modeler.get('elementRegistry');
    const endEvents = elementRegistry.filter(
      (el: BpmnTypes.BpmnElement) => el.type === 'bpmn:EndEvent'
    );
    return endEvents.length > 0
      ? []
      : ['Process must have at least one end event'];
  },
};

// Service task implementation rule
const serviceTaskImplementationRule: ValidationRule = {
  validate(modeler: BpmnTypes.ExtendedBpmnModeler): string[] {
    const elementRegistry = modeler.get('elementRegistry');
    const errors: string[] = [];

    const serviceTasks = elementRegistry.filter(
      (el: BpmnTypes.BpmnElement) => el.type === 'bpmn:ServiceTask'
    );
    serviceTasks.forEach((task: BpmnTypes.BpmnElement) => {
      const extensions = task.businessObject.extensionElements?.values || [];
      const hasImplementation = extensions.some(
        (ext: BpmnTypes.ExtensionElement) =>
          ext.$type === 'pythmata:ServiceTaskConfig' && !!ext.taskName
      );

      if (!hasImplementation) {
        errors.push(
          `Service task "${task.id}" is missing implementation details`
        );
      }
    });

    return errors;
  },
};

// Define all validation rules
const validationRules: ValidationRule[] = [
  startEventRule,
  endEventRule,
  serviceTaskImplementationRule,
  // Add more rules as needed
];

// Constants
const DRAWER_WIDTH = 400;
const CHAT_DRAWER_WIDTH = 450;
const DEFAULT_EMPTY_BPMN = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1"/>
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
        <dc:Bounds x="156" y="81" width="36" height="36"/>
      </bpmndi:BPMNShape>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>`;
const DEFAULT_EMPTY_DMN = `<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" 
             xmlns:dmndi="https://www.omg.org/spec/DMN/20191111/DMNDI/" 
             xmlns:dc="http://www.omg.org/spec/DMN/20180521/DC/" 
             namespace="http://camunda.org/schema/1.0/dmn">
  <decision id="Decision_1" name="Decision 1">
    <decisionTable id="DecisionTable_1">
      <input id="Input_1">
        <inputExpression id="InputExpression_1" typeRef="string">
          <text>input1</text>
        </inputExpression>
      </input>
      <output id="Output_1" typeRef="string" />
    </decisionTable>
  </decision>
  <dmndi:DMNDI>
    <dmndi:DMNDiagram id="DMNDiagram_1">
      <dmndi:DMNShape id="DMNShape_1" dmnElementRef="Decision_1">
        <dc:Bounds height="80" width="180" x="160" y="100" />
      </dmndi:DMNShape>
    </dmndi:DMNDiagram>
  </dmndi:DMNDI>
</definitions>`;

/**
 * ProcessDesigner component
 *
 * A component for designing BPMN processes with a visual modeler and XML editor.
 *
 * @returns ProcessDesigner component
 */
/**
 * ProcessDesigner component
 *
 * Optimized for maintainability and scalability.
 *
 * @returns ProcessDesigner component
 */
const ProcessDesigner: React.FC = () => {
  // Router hooks
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const dmnContainerRef = useRef<HTMLDivElement>(null);
  const propertiesPanelRef = useRef<HTMLDivElement>(null);
  const modelerRef = useRef<BpmnTypes.ExtendedBpmnModeler | undefined>(
    undefined
  );
  const dmnModelerRef = useRef<DmnTypes.ExtendedDmnModeler | undefined>(undefined);

  // State - Process data
  const [processName, setProcessName] = useState<string>('');
  const [bpmnXml, setBpmnXml] = useState<string>(DEFAULT_EMPTY_BPMN);
  const [dmnXml, setDmnXml] = useState<string>(DEFAULT_EMPTY_DMN);
  const [variableDefinitions, setVariableDefinitions] = useState<
    ProcessVariableDefinition[]
  >([]);

  // State - UI
  const [activeTab, setActiveTab] = useState<'modeler' | 'xmlEditor' | 'dmnModeler' | 'dmnXmlEditor'>(
    'modeler'
  );
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [xmlError, setXmlError] = useState<string | null>(null);
  const [dmnXmlError, setDmnXmlError] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState<boolean>(false);
  const [snackbarMessage, setSnackbarMessage] = useState<string>('');

  // State - Drawers
  const [variablesDrawerOpen, setVariablesDrawerOpen] =
    useState<boolean>(false);
  const [elementDrawerOpen, setElementDrawerOpen] = useState<boolean>(false);
  const [chatDrawerOpen, setChatDrawerOpen] = useState<boolean>(false);
  const [selectedElement, setSelectedElement] = useState<string | null>(null);

  // Load process data
  useEffect(() => {
    const loadProcess = async () => {
      if (id) {
        try {
          const response = await apiService.getProcessDefinition(id);
          const { name, bpmnXml, variableDefinitions } = response.data;

          // Check schema compatibility
          const compatibility = checkSchemaCompatibility(bpmnXml);
          if (!compatibility.compatible && compatibility.message) {
            setError(compatibility.message);
          }

          setProcessName(name);
          setBpmnXml(bpmnXml);
          setVariableDefinitions(variableDefinitions || []);
        } catch (error) {
          console.error('Failed to load process:', error);
          setError('Failed to load process. Please try again.');
          return;
        }
      } else {
        setProcessName('New Process');
        setBpmnXml(DEFAULT_EMPTY_BPMN);
      }
      setLoading(false);
    };

    loadProcess();
  }, [id]);

  /**
   * Check schema compatibility
   *
   * Verifies if the BPMN XML uses a compatible schema version
   *
   * @param xml - The BPMN XML to check
   * @returns Object with compatibility status and optional message
   */
  const checkSchemaCompatibility = (
    xml: string
  ): { compatible: boolean; message?: string } => {
    // Check for namespace declaration
    const hasNamespace = xml.includes(
      'xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"'
    );
    if (!hasNamespace) {
      return {
        compatible: false,
        message:
          'Process XML is missing the Pythmata namespace declaration. This process may not be compatible.',
      };
    }

    // Check for specific schema version (could be extended for multiple versions)
    const schemaVersionMatch = xml.match(/pythmata:schema\/(\d+\.\d+)\/bpmn/);
    if (!schemaVersionMatch) {
      return {
        compatible: true,
        message:
          'Process XML does not specify a schema version. Using default compatibility.',
      };
    }

    const schemaVersion = schemaVersionMatch[1];

    // Version-specific compatibility checks
    if (schemaVersion === '1.0') {
      return { compatible: true };
    } else {
      return {
        compatible: false,
        message: `Process uses schema version ${schemaVersion}, but this editor supports version 1.0. Some features may not work correctly.`,
      };
    }
  };

  // Initialize BPMN modeler
  useEffect(() => {
    if (loading || !containerRef.current) return;

    const initializeModeler = async () => {
      try {
        if (!containerRef.current) return;

        // Create modeler instance
        modelerRef.current = new BpmnModeler({
          container: containerRef.current,
          // Use type assertion to include custom properties
          moddleExtensions: {
            pythmata: pythmataModdleDescriptor,
          },
          // Configure palette to appear on the left side
          palette: {
            open: true,
          },
        } as BpmnTypes.BpmnModelerOptions) as BpmnTypes.ExtendedBpmnModeler;

        // Apply CSS classes for styling
        if (containerRef.current) {
          containerRef.current.classList.add(
            'bpmn-container-with-left-palette',
            'bpmn-container-with-overlay-panels'
          );
        }

        // Import XML to the modeler
        await modelerRef.current.importXML(bpmnXml);

        // Set up event listeners inline
        {
          const eventBus = modelerRef.current.get('eventBus');
          eventBus.on(
            'selection.changed',
            (e: { newSelection: Array<BpmnTypes.BpmnElement> }) => {
              const selection = e.newSelection;
              if (selection.length === 1) {
                const element = selection[0];
                if (element) {
                  setSelectedElement(element.id);
                } else {
                  setElementDrawerOpen(false);
                }
              } else {
                setElementDrawerOpen(false);
              }
            }
          );
          eventBus.on(
            'element.dblclick',
            (e: { element: BpmnTypes.BpmnElement }) => {
              if (e.element) {
                setSelectedElement(e.element.id);
                setElementDrawerOpen(true);
              }
            }
          );
          let updateXmlTimeout: NodeJS.Timeout | null = null;
          eventBus.on('commandStack.changed', async () => {
            if (modelerRef.current && activeTab === 'modeler') {
              if (updateXmlTimeout) {
                clearTimeout(updateXmlTimeout);
              }
              updateXmlTimeout = setTimeout(async () => {
                const modeler = modelerRef.current;
                if (!modeler) return;
                try {
                  const { xml } = await modeler.saveXML({ format: true });
                  setBpmnXml(xml);
                } catch (error) {
                  console.error(
                    'Failed to update XML after diagram change:',
                    error
                  );
                }
              }, 500);
            }
          });
        }

        // Position the palette on the left
        positionPalette();
      } catch (error) {
        console.error('Failed to initialize modeler:', error);
        setError(
          'Failed to initialize process designer. Please try refreshing the page.'
        );
      }
    };

    initializeModeler();

    // Cleanup function
    return () => {
      if (modelerRef.current) {
        modelerRef.current.destroy();
        modelerRef.current = undefined;
      }
    };
  }, [loading, bpmnXml, activeTab]);

  // Initialize DMN modeler
  useEffect(() => {
    if (loading || !dmnContainerRef.current || activeTab !== 'dmnModeler') return;

    const initializeDmnModeler = async () => {
      try {
        if (!dmnContainerRef.current) return;

        // Create DMN modeler instance
        dmnModelerRef.current = new DmnModeler({
          container: dmnContainerRef.current,
          drd: {
            additionalModules: []
          },
          decisionTable: {
            additionalModules: []
          },
          literalExpression: {
            additionalModules: []
          }
        } as DmnTypes.DmnModelerOptions) as DmnTypes.ExtendedDmnModeler;

        // Import XML to the modeler
        await dmnModelerRef.current.importXML(dmnXml);

        // Set up event listeners
        const activeViewer = dmnModelerRef.current.getActiveViewer();

        {
          const eventBus = activeViewer.get('eventBus');
          eventBus.on(
            'selection.changed',
            (e: { newSelection: Array<DmnTypes.DmnElement> }) => {
              const selection = e.newSelection;
              if (selection.length === 1) {
                const element = selection[0];
                if (element) {
                  setSelectedElement(element.id);
                } else {
                  setElementDrawerOpen(false);
                }
              } else {
                setElementDrawerOpen(false);
              }
            }
          );
          eventBus.on(
            'element.dblclick',
            (e: { element: DmnTypes.DmnElement }) => {
              if (e.element) {
                setSelectedElement(e.element.id);
                setElementDrawerOpen(true);
              }
            }
          );
          let updateXmlTimeout: NodeJS.Timeout | null = null;
          eventBus.on('commandStack.changed', async () => {
            if (dmnModelerRef.current && activeTab === 'dmnModeler') {
              if (updateXmlTimeout) {
                clearTimeout(updateXmlTimeout);
              }
              updateXmlTimeout = setTimeout(async () => {
                const modeler = dmnModelerRef.current;
                if (!modeler) return;
                try {
                  const { xml } = await modeler.saveXML({ format: true });
                  setDmnXml(xml);
                } catch (error) {
                  console.error(
                    'Failed to update XML after diagram change:',
                    error
                  );
                }
              }, 500);
            }
          });
        }
      } catch (error) {
        console.error('Failed to initialize DMN modeler:', error);
        setError('Failed to initialize DMN modeler. Please try refreshing the page.');
      }
    };

    initializeDmnModeler();
    // Cleanup function
    return () => {
      if (dmnModelerRef.current) {
        dmnModelerRef.current.destroy();
        dmnModelerRef.current = undefined;
      }
    };

  }, [loading, dmnXml, activeTab]);

  // Removed unused setupEventListeners function

  // Position the palette on the left side
  const positionPalette = () => {
    setTimeout(() => {
      const paletteElement = document.querySelector('.djs-palette');
      if (paletteElement) {
        (paletteElement as HTMLElement).style.left = '20px';
        (paletteElement as HTMLElement).style.right = 'auto';
      }

      // Set up a MutationObserver to ensure the palette stays on the left
      const observer = new MutationObserver((mutations) => {
        mutations.forEach(() => {
          const palette = document.querySelector('.djs-palette');
          if (palette) {
            (palette as HTMLElement).style.left = '20px';
            (palette as HTMLElement).style.right = 'auto';
          }
        });
      });

      // Start observing the container for changes
      if (containerRef.current) {
        observer.observe(containerRef.current, {
          childList: true,
          subtree: true,
          attributes: true,
          attributeFilter: ['style'],
        });
      }
    }, 100);
  };

  // Copy XML to clipboard
  const handleCopyXml = async () => {
    if (!modelerRef.current) return;

    try {
      const { xml } = await modelerRef.current.saveXML({ format: true });
      await navigator.clipboard.writeText(xml);
      alert('XML copied to clipboard');
    } catch (error) {
      console.error('Failed to copy XML:', error);
      alert('Failed to copy XML. Please try again.');
    }
  };

  /**
   * Validate the process
   *
   * Checks if the process meets all validation rules
   *
   * @returns Object with validation status and errors
   */
  const validateProcess = useCallback((): {
    valid: boolean;
    errors: string[];
  } => {
    const modeler = modelerRef.current;
    if (!modeler) {
      return { valid: false, errors: ['Modeler not initialized'] };
    }

    try {
      // Run all validation rules
      const errors = validationRules.flatMap((rule) => rule.validate(modeler));

      return {
        valid: errors.length === 0,
        errors,
      };
    } catch (error) {
      console.error('Validation error:', error);
      return {
        valid: false,
        errors: [
          `Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        ],
      };
    }
  }, []);

  // Save process
  const handleSave = async () => {
    if (!modelerRef.current || !processName) return;

    try {
      setSaving(true);

      // Basic validation
      const validation = validateProcess();
      if (!validation.valid) {
        // Show errors in a dialog
        alert(
          `Cannot save process with errors:\n\n${validation.errors.join('\n')}`
        );
        setSaving(false);
        return;
      }

      const { xml } = await modelerRef.current.saveXML({ format: true });

      // Convert variable definitions to backend format
      const convertedVariableDefinitions =
        convertDefinitionsToBackend(variableDefinitions);

      const processData = {
        name: processName,
        bpmnXml: xml,
        variableDefinitions: convertedVariableDefinitions,
      };

      if (id) {
        // Update existing process
        await apiService.updateProcessDefinition(id, processData);
      } else {
        // Create new process
        await apiService.createProcessDefinition({
          ...processData,
          version: 1,
        });
      }

      // Navigate back to process list
      navigate('/processes');
    } catch (error) {
      console.error('Failed to save process:', error);
      alert('Failed to save process. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Apply XML from editor to modeler
  const applyXmlChanges = async () => {
    if (!modelerRef.current) return;
    setXmlError(null); // Clear previous errors

    try {
      const result = await modelerRef.current.importXML(bpmnXml);

      // Check for warnings
      if (result.warnings && result.warnings.length > 0) {
        setSnackbarMessage(
          'XML applied with warnings. Check console for details.'
        );
        setSnackbarOpen(true);
        console.warn('XML import warnings:', result.warnings);
      } else {
        setSnackbarMessage('XML applied successfully');
        setSnackbarOpen(true);
      }
    } catch (error) {
      console.error('Error applying XML changes:', error);

      // Extract meaningful error message
      let errorMessage = 'Unknown error occurred';

      if (error instanceof Error) {
        errorMessage = error.message;

        // Try to extract more specific error details
        if (error.message.includes('unparsable')) {
          errorMessage =
            'XML syntax error. Please check for missing tags or invalid characters.';
        } else if (error.message.includes('unknown element')) {
          const match = error.message.match(/unknown element <([^>]+)>/);
          if (match) {
            errorMessage = `Unknown element "${match[1]}". Check for typos or missing namespace declarations.`;
          }
        }
      }

      setXmlError(errorMessage);
    }
  };

  // Apply DMN XML from editor to DMN modeler
  const applyDmnXmlChanges = async () => {
    if (!dmnModelerRef.current) return;
    setDmnXmlError(null); // Clear previous errors

    try {
      const result = await dmnModelerRef.current.importXML(dmnXml);

      // Check for warnings
      if (result.warnings && result.warnings.length > 0) {
        setSnackbarMessage(
          'XML applied with warnings. Check console for details.'
        );
        setSnackbarOpen(true);
        console.warn('XML import warnings:', result.warnings);
      } else {
        setSnackbarMessage('XML applied successfully');
        setSnackbarOpen(true);
      }
    } catch (error) {
      console.error('Error applying XML changes:', error);

      // Extract meaningful error message
      let errorMessage = 'Unknown error occurred';

      if (error instanceof Error) {
        errorMessage = error.message;

        // Try to extract more specific error details
        if (error.message.includes('unparsable')) {
          errorMessage =
            'XML syntax error. Please check for missing tags or invalid characters.';
        } else if (error.message.includes('unknown element')) {
          const match = error.message.match(/unknown element <([^>]+)>/);
          if (match) {
            errorMessage = `Unknown element "${match[1]}". Check for typos or missing namespace declarations.`;
          }
        }
      }

      setDmnXmlError(errorMessage);
    }
  };

  // Handle XML changes from chat panel
  const handleApplyXmlFromChat = (xml: string) => {
    if (modelerRef.current) {
      try {
        modelerRef.current
          .importXML(xml)
          .then(() => {
            console.warn('XML changes applied successfully');
          })
          .catch((err: Error) => {
            console.error('Error applying XML changes:', err);
          });
      } catch (importError) {
        console.error('Error applying XML changes:', importError);
      }
    }
  };

  // Loading state
  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        {error ? (
          <Typography color="error">{error}</Typography>
        ) : (
          <CircularProgress />
        )}
      </Box>
    );
  }

  return (
    <Box
      sx={{
        height: 'calc(100vh - 64px)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbarOpen(false)}
          severity="success"
          sx={{ width: '100%' }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
      {/* Toolbar */}
      <AppBar position="static" color="default" elevation={0}>
        <Toolbar sx={{ gap: 2 }}>
          <TextField
            value={processName}
            onChange={(e) => setProcessName(e.target.value)}
            variant="standard"
            placeholder="Process Name"
            sx={{ flexGrow: 1 }}
          />
          <IconButton
            color="primary"
            onClick={() => setVariablesDrawerOpen(true)}
            title="Process Variables"
          >
            <SettingsIcon />
          </IconButton>
          <IconButton
            color="primary"
            onClick={() => setChatDrawerOpen(true)}
            title="Process Assistant"
          >
            <ChatIcon />
          </IconButton>
          <Button
            variant="outlined"
            startIcon={<ContentCopyIcon />}
            onClick={handleCopyXml}
            disabled={loading || saving}
            sx={{ mr: 1 }}
            title="Copy process XML to clipboard"
          >
            Copy XML
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </Toolbar>
      </AppBar>

      {/* Tabs */}
      <Tabs
        value={activeTab}
        onChange={(_e, newValue: 'modeler' | 'xmlEditor' | 'dmnModeler' | 'dmnXmlEditor') =>
          setActiveTab(newValue)
        }
        indicatorColor="primary"
        textColor="primary"
        sx={{ borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab label="BPMN Modeler" value="modeler" />
        <Tab label="BPMN XML Editor" value="xmlEditor" />
        <Tab label="DMN Modeler" value="dmnModeler" />
        <Tab label="DMN XML Editor" value="dmnXmlEditor" />
      </Tabs>

      {/* Content */}
      {activeTab === 'modeler' ? (
        <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
          <Paper
            sx={{
              flexGrow: 1,
              position: 'relative',
              bgcolor: '#fff',
              overflow: 'hidden',
            }}
          >
            <div
              ref={containerRef}
              style={{
                width: '100%',
                height: '100%',
                position: 'relative',
              }}
            >
              <div
                ref={propertiesPanelRef}
                style={{
                  position: 'absolute',
                  right: '20px',
                  top: '20px',
                  zIndex: 100,
                }}
              />
            </div>
          </Paper>
        </Box>
      ) : activeTab === 'xmlEditor' ? (
        <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <Box
            sx={{
              flexGrow: 1,
              overflow: 'auto',
              maxHeight: 'calc(100% - 80px)',
            }}
          >
            <MonacoEditor
              language="xml"
              value={bpmnXml}
              onChange={(newValue: string | undefined): void =>
                setBpmnXml(newValue || '')
              }
              options={{ theme: 'light', automaticLayout: true }}
              height="100%"
            />
          </Box>
          <Box sx={{ mt: 2 }}>
            {xmlError && (
              <Paper
                sx={{
                  p: 2,
                  mb: 2,
                  bgcolor: 'error.light',
                  color: 'error.contrastText',
                }}
              >
                <Typography variant="subtitle2">Error in XML:</Typography>
                <Typography
                  variant="body2"
                  component="pre"
                  sx={{ whiteSpace: 'pre-wrap' }}
                >
                  {xmlError}
                </Typography>
              </Paper>
            )}
            <Button variant="contained" onClick={applyXmlChanges}>
              Apply XML
            </Button>
          </Box>
        </Box>
      ) : activeTab === 'dmnModeler' ? (
        <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
          <Paper
            sx={{
              flexGrow: 1,
              position: 'relative',
              bgcolor: '#fff',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            <div
              ref={dmnContainerRef}
              style={{
                width: '100%',
                height: '100%'
              }}
            />
          </Paper>
        </Box>
      ) : (
        <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <Box
            sx={{
              flexGrow: 1,
              overflow: 'auto',
              maxHeight: 'calc(100% - 80px)',
            }}
          >
            <MonacoEditor
              language="xml"
              value={dmnXml}
              onChange={(newValue: string | undefined): void =>
                setDmnXml(newValue || '')
              }
              options={{ theme: 'light', automaticLayout: true }}
              height="100%"
            />
          </Box>
          <Box sx={{ mt: 2 }}>
            {dmnXmlError && (
              <Paper
                sx={{
                  p: 2,
                  mb: 2,
                  bgcolor: 'error.light',
                  color: 'error.contrastText',
                }}
              >
                <Typography variant="subtitle2">Error in DMN XML:</Typography>
                <Typography
                  variant="body2"
                  component="pre"
                  sx={{ whiteSpace: 'pre-wrap' }}
                >
                  {dmnXmlError}
                </Typography>
              </Paper>
            )}
            <Button variant="contained" onClick={applyDmnXmlChanges}>
              Apply DMN XML
            </Button>
          </Box>
        </Box>
      ) }

      {/* Variables Drawer */}
      <Drawer
        anchor="right"
        open={variablesDrawerOpen}
        onClose={() => setVariablesDrawerOpen(false)}
        sx={{
          '& .MuiDrawer-paper': {
            width: `${DRAWER_WIDTH}px`,
            p: 3,
          },
        }}
      >
        <VariableDefinitionsPanel
          variables={variableDefinitions}
          onChange={setVariableDefinitions}
        />
      </Drawer>

      {/* Element Properties Drawer */}
      <Drawer
        anchor="right"
        open={elementDrawerOpen}
        onClose={() => setElementDrawerOpen(false)}
        sx={{
          '& .MuiDrawer-paper': {
            width: `${DRAWER_WIDTH}px`,
            p: 0,
          },
        }}
      >
        {selectedElement && modelerRef.current && (
          <ElementPanel
            elementId={selectedElement}
            modeler={modelerRef.current}
            onClose={() => setElementDrawerOpen(false)}
          />
        )}
      </Drawer>

      {/* Chat Drawer */}
      <Drawer
        anchor="right"
        open={chatDrawerOpen}
        onClose={() => setChatDrawerOpen(false)}
        sx={{
          '& .MuiDrawer-paper': {
            width: `${CHAT_DRAWER_WIDTH}px`,
            p: 0,
          },
        }}
      >
        <ChatPanel
          processId={id}
          modeler={modelerRef.current}
          onClose={() => setChatDrawerOpen(false)}
          onApplyXml={handleApplyXmlFromChat}
        />
      </Drawer>
    </Box>
  );
};

export default ProcessDesigner;
