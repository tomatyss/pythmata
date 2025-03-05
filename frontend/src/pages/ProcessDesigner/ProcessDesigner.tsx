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
import ChatPanel from '@/components/shared/ChatPanel';
import VariableDefinitionsPanel from '@/components/shared/VariableDefinitionsPanel/VariableDefinitionsPanel';
import ElementPanel from '@/components/shared/ElementPanel';
import { ProcessVariableDefinition } from '@/types/process';
import BpmnModeler from 'bpmn-js/lib/Modeler';
import 'bpmn-js/dist/assets/diagram-js.css';

// Define types for BPMN elements and properties
interface BusinessObject {
  extensionElements?: {
    values: ExtensionElement[];
  };
}

interface BpmnElement {
  id: string;
  type: string;
  businessObject: BusinessObject;
}

// Define types for extension elements
interface ExtensionElement {
  $type: string;
  taskName?: string;
  properties?: {
    values: PropertyValue[];
  };
}

interface PropertyValue {
  name: string;
  value: string;
}

// Define types for the modeler modules
interface ElementRegistry {
  get(id: string): BpmnElement;
}

interface Modeling {
  updateProperties(
    element: BpmnElement,
    properties: Record<string, unknown>
  ): void;
}

interface Moddle {
  create<T>(type: string, properties?: Record<string, unknown>): T;
}

// Used in the eventBus.on callback

interface EventBus {
  on<T = unknown>(event: string, callback: (event: T) => void): void;
}

// Define a mapping of module names to their types
interface ModuleTypeMap {
  elementRegistry: ElementRegistry;
  modeling: Modeling;
  moddle: Moddle;
  eventBus: EventBus;
}

// Define a type for the modeler with the methods we need
type ModelerModule = keyof ModuleTypeMap;

type ExtendedBpmnModeler = BpmnModeler & {
  get<T extends ModelerModule>(name: T): ModuleTypeMap[T];
};
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css';

// Import pythmata moddle extension for service tasks
import pythmataModdleDescriptor from '@/components/BpmnModeler/moddle/pythmata.json';

// Import palette module for configuration

// Import custom CSS to position palette on the left and properties panel as overlay
import '@/components/BpmnModeler/palette-left.css';
import '@/components/BpmnModeler/properties-panel-overlay.css';

// Default empty BPMN diagram
const emptyBpmn = `<?xml version="1.0" encoding="UTF-8"?>
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

const ProcessDesigner = () => {
  const [activeTab, setActiveTab] = useState<'modeler' | 'xmlEditor'>(
    'modeler'
  );
  const { id } = useParams();
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const propertiesPanelRef = useRef<HTMLDivElement>(null);
  const modelerRef = useRef<ExtendedBpmnModeler | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [processName, setProcessName] = useState('');
  const [bpmnXml, setBpmnXml] = useState(emptyBpmn);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [variablesDrawerOpen, setVariablesDrawerOpen] = useState(false);
  const [elementDrawerOpen, setElementDrawerOpen] = useState(false);
  const [chatDrawerOpen, setChatDrawerOpen] = useState(false);
  const [selectedElement, setSelectedElement] = useState<string | null>(null);
  const [variableDefinitions, setVariableDefinitions] = useState<
    ProcessVariableDefinition[]
  >([]);

  useEffect(() => {
    const loadProcess = async () => {
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
        setBpmnXml(emptyBpmn);
      }
      setLoading(false);
    };

    loadProcess();
  }, [id]);

  useEffect(() => {
    if (loading || !containerRef.current) return;

    const initializeModeler = async () => {
      try {
        if (!containerRef.current || !propertiesPanelRef.current) return;

        // Define a more complete type for BpmnModeler options
        interface BpmnModelerOptions {
          container: HTMLElement;
          moddleExtensions?: Record<string, unknown>;
          palette?: {
            open: boolean;
          };
          keyboard?: {
            bindTo: Document;
          };
        }

        // Use type assertion to tell TypeScript to trust us about the type
        modelerRef.current = new BpmnModeler({
          container: containerRef.current as HTMLElement,
          moddleExtensions: {
            pythmata: pythmataModdleDescriptor,
          },
          // Configure palette to appear on the left side
          palette: {
            open: true,
          },
        } as BpmnModelerOptions) as ExtendedBpmnModeler;

        // Apply classes to the container to help with CSS targeting
        if (containerRef.current) {
          containerRef.current.classList.add(
            'bpmn-container-with-left-palette',
            'bpmn-container-with-overlay-panels'
          );
        }

        await modelerRef.current.importXML(bpmnXml);

        // Add event listener for element selection
        if (modelerRef.current) {
          const eventBus = modelerRef.current.get('eventBus');
          // Listen for element selection
          eventBus.on(
            'selection.changed',
            (e: { newSelection: Array<{ id: string; type: string }> }) => {
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
          eventBus.on(
            'element.dblclick',
            (e: { element: { id: string; type: string } }) => {
              if (e.element) {
                setSelectedElement(e.element.id);
                setElementDrawerOpen(true);
              }
            }
          );
        }

        // After the modeler is initialized, force the palette to the left side
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
      } catch (error) {
        console.error('Failed to initialize modeler:', error);
        setError(
          'Failed to initialize process designer. Please try refreshing the page.'
        );
      }
    };

    initializeModeler();

    return () => {
      if (modelerRef.current) {
        modelerRef.current.destroy();
        modelerRef.current = undefined;
      }
    };
  }, [loading, bpmnXml, activeTab]); // Reinitialize when activeTab changes

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

  const handleSave = async () => {
    if (!modelerRef.current || !processName) return;

    try {
      setSaving(true);
      const { xml } = await modelerRef.current.saveXML({ format: true });

      if (id) {
        // Update existing process
        await apiService.updateProcessDefinition(id, {
          name: processName,
          bpmnXml: xml,
          variableDefinitions: variableDefinitions,
        });
      } else {
        // Create new process
        await apiService.createProcessDefinition({
          name: processName,
          bpmnXml: xml,
          version: 1,
          variableDefinitions: variableDefinitions,
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

      <Tabs
        value={activeTab}
        onChange={(e, newValue) => setActiveTab(newValue)}
        indicatorColor="primary"
        textColor="primary"
        sx={{ borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab label="Modeler" value="modeler" />
        <Tab label="XML Editor" value="xmlEditor" />
      </Tabs>

      {activeTab === 'modeler' && (
        <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
          {/* BPMN Canvas with overlaid Properties Panel */}
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
              {/* Properties Panel as overlay */}
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
      )}

      {activeTab === 'xmlEditor' && (
        <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
            <MonacoEditor
              language="xml"
              value={bpmnXml}
              onChange={(newValue: string | undefined) =>
                setBpmnXml(newValue || '')
              }
              options={{ theme: 'light', automaticLayout: true }}
              height="100%"
            />
          </Box>
          <Button
            variant="contained"
            onClick={() => {
              try {
                if (modelerRef.current) {
                  modelerRef.current.importXML(bpmnXml);
                }
                alert('XML applied successfully');
              } catch {
                alert('Invalid XML. Please fix the errors and try again.');
              }
            }}
            sx={{ mt: 2 }}
          >
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
            width: '400px',
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
            width: '400px',
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
            width: '450px',
            p: 0,
          },
        }}
      >
        <ChatPanel
          processId={id}
          modeler={modelerRef.current}
          onClose={() => setChatDrawerOpen(false)}
          onApplyXml={(xml) => {
            if (modelerRef.current) {
              modelerRef.current.importXML(xml);
            }
          }}
        />
      </Drawer>
    </Box>
  );
};

export default ProcessDesigner;
