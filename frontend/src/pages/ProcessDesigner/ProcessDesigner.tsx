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
} from '@mui/material';
import {
  Save as SaveIcon,
  Settings as SettingsIcon,
  ContentCopy as ContentCopyIcon,
} from '@mui/icons-material';
import VariableDefinitionsPanel from '@/components/shared/VariableDefinitionsPanel/VariableDefinitionsPanel';
import { ProcessVariableDefinition } from '@/types/process';
import BpmnModeler from 'bpmn-js/lib/Modeler';
import 'bpmn-js/dist/assets/diagram-js.css';
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css';

// Default empty BPMN diagram
const emptyBpmn = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
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
  const { id } = useParams();
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const modelerRef = useRef<BpmnModeler | null>(null);
  const [loading, setLoading] = useState(true);
  const [processName, setProcessName] = useState('');
  const [bpmnXml, setBpmnXml] = useState(emptyBpmn);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
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
        if (!containerRef.current) return;

        modelerRef.current = new BpmnModeler({
          container: containerRef.current as HTMLElement,
        });

        await modelerRef.current.importXML(bpmnXml);
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
        modelerRef.current = null;
      }
    };
  }, [loading, bpmnXml]); // Add bpmnXml as dependency to reinitialize when it changes

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
            onClick={() => setDrawerOpen(true)}
            title="Process Settings"
          >
            <SettingsIcon />
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

      <Paper
        sx={{
          flexGrow: 1,
          position: 'relative',
          bgcolor: '#fff',
          overflow: 'hidden',
          mr: 'var(--palette-width)', // Space for palette
        }}
      >
        <div
          ref={containerRef}
          style={{
            width: '100%',
            height: '100%',
          }}
        />
      </Paper>

      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
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
    </Box>
  );
};

export default ProcessDesigner;
