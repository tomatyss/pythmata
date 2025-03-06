import { useEffect, useRef, useState } from 'react';
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
import '@/components/BpmnModeler/palette-left.css';
import '@/components/BpmnModeler/properties-panel-overlay.css';

// Import pythmata moddle extension for service tasks
import pythmataModdleDescriptor from '@/components/BpmnModeler/moddle/pythmata.json';

// Import types
import * as BpmnTypes from './types';

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

/**
 * ProcessDesigner component
 *
 * A component for designing BPMN processes with a visual modeler and XML editor.
 *
 * @returns ProcessDesigner component
 */
const ProcessDesigner = (): React.ReactElement => {
  // Router hooks
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const propertiesPanelRef = useRef<HTMLDivElement>(null);
  const modelerRef = useRef<BpmnTypes.ExtendedBpmnModeler | undefined>(
    undefined
  );

  // State - Process data
  const [processName, setProcessName] = useState<string>('');
  const [bpmnXml, setBpmnXml] = useState<string>(DEFAULT_EMPTY_BPMN);
  const [variableDefinitions, setVariableDefinitions] = useState<
    ProcessVariableDefinition[]
  >([]);

  // State - UI
  const [activeTab, setActiveTab] = useState<'modeler' | 'xmlEditor'>(
    'modeler'
  );
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // State - Drawers
  const [variablesDrawerOpen, setVariablesDrawerOpen] =
    useState<boolean>(false);
  const [elementDrawerOpen, setElementDrawerOpen] = useState<boolean>(false);
  const [chatDrawerOpen, setChatDrawerOpen] = useState<boolean>(false);
  const [selectedElement, setSelectedElement] = useState<string | null>(null);

  // Load process data
  useEffect(() => {
    const loadProcess = async (): Promise<void> => {
      if (id) {
        try {
          const response = await apiService.getProcessDefinition(id);
          const { name, bpmnXml, variableDefinitions } = response.data;
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

  // Initialize BPMN modeler
  useEffect(() => {
    if (loading || !containerRef.current) return;

    const initializeModeler = async (): Promise<void> => {
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

        // Set up event listeners
        setupEventListeners();

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

  // Set up event listeners for the modeler
  const setupEventListeners = (): void => {
    if (!modelerRef.current) return;

    const eventBus = modelerRef.current.get('eventBus');

    // Listen for element selection
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

    // Listen for element double-click to open properties panel
    eventBus.on('element.dblclick', (e: { element: BpmnTypes.BpmnElement }) => {
      if (e.element) {
        setSelectedElement(e.element.id);
        setElementDrawerOpen(true);
      }
    });
  };

  // Position the palette on the left side
  const positionPalette = (): void => {
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
  const handleCopyXml = async (): Promise<void> => {
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

  // Save process
  const handleSave = async (): Promise<void> => {
    if (!modelerRef.current || !processName) return;

    try {
      setSaving(true);
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
  const applyXmlChanges = (): void => {
    try {
      if (modelerRef.current) {
        modelerRef.current.importXML(bpmnXml);
        alert('XML applied successfully');
      }
    } catch (error) {
      alert(
        'Invalid XML. Please fix the errors and try again. See console for details.'
      );
      console.error('Error applying XML changes:', error);
    }
  };

  // Handle XML changes from chat panel
  const handleApplyXmlFromChat = (xml: string): void => {
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
        onChange={(_e, newValue: 'modeler' | 'xmlEditor') =>
          setActiveTab(newValue)
        }
        indicatorColor="primary"
        textColor="primary"
        sx={{ borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab label="Modeler" value="modeler" />
        <Tab label="XML Editor" value="xmlEditor" />
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
              value={bpmnXml}
              onChange={(newValue: string | undefined): void =>
                setBpmnXml(newValue || '')
              }
              options={{ theme: 'light', automaticLayout: true }}
              height="100%"
            />
          </Box>
          <Button variant="contained" onClick={applyXmlChanges} sx={{ mt: 2 }}>
            Apply XML
          </Button>
        </Box>
      )}

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
