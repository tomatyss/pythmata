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
} from '@mui/material';
import { Save as SaveIcon } from '@mui/icons-material';
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
  const modelerRef = useRef<any>(null);
  const [loading, setLoading] = useState(true);
  const [processName, setProcessName] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    console.log('ProcessDesigner mounted');
    if (id) {
      setProcessName('Existing Process');
    } else {
      setProcessName('New Process');
    }
    setLoading(false);
  }, [id]);

  useEffect(() => {
    if (loading || !containerRef.current) return;

    console.log('Initializing BPMN modeler...');
    console.log('Container ref:', containerRef.current);
    console.log('Container dimensions:', {
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    });

    try {
      modelerRef.current = new BpmnModeler({
        container: containerRef.current,
        keyboard: {
          bindTo: document,
        },
      });
      console.log('BpmnModeler instance created:', modelerRef.current);

      modelerRef.current.importXML(emptyBpmn).then(() => {
        console.log('BPMN XML imported successfully');
      });
    } catch (error: any) {
      console.error('Error initializing BPMN modeler:', error);
      if (error instanceof Error) {
        console.error('Error details:', {
          name: error.name,
          message: error.message,
          stack: error.stack,
        });
      }
      setError(
        'Failed to initialize process designer. Please try refreshing the page.'
      );
    }

    return () => {
      if (modelerRef.current) {
        console.log('Cleaning up BPMN modeler');
        modelerRef.current.destroy();
        modelerRef.current = null;
      }
    };
  }, [loading]);

  const handleSave = async () => {
    if (!modelerRef.current || !processName) return;

    try {
      setSaving(true);
      const { xml } = await modelerRef.current.saveXML({ format: true });

      if (id) {
        // Update existing process
        await apiService.updateProcessDefinition(id, {
          name: processName,
          bpmn_xml: xml,
        });
      } else {
        // Create new process
        await apiService.createProcessDefinition({
          name: processName,
          bpmn_xml: xml,
          version: 1,
        });
      }

      // Navigate back to process list
      navigate('/processes');
    } catch (error) {
      console.error('Error saving process:', error);
      // Show error notification
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
    </Box>
  );
};

export default ProcessDesigner;
