import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiService from '@/services/api';
import ProcessDiagramViewer from '@/components/shared/ProcessDiagramViewer';
import { TokenData } from '@/hooks/useProcessTokens';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Tabs,
  Tab,
  Breadcrumbs,
  Link,
} from '@mui/material';

interface ProcessDetails {
  name: string;
  bpmn_xml: string;
}

interface ProcessInstance {
  id: string;
  status: string;
}

const ProcessDiagram = () => {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [process, setProcess] = useState<ProcessDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [tokens, setTokens] = useState<TokenData[]>([]);
  const [activeInstances, setActiveInstances] = useState<ProcessInstance[]>([]);
  const navigate = useNavigate();

  // Fetch active instances and their tokens
  // Auto-select Active Instances tab when instances exist
  useEffect(() => {
    const fetchActiveInstances = async () => {
      if (!id) return;

      try {
        const response = await apiService.getProcessInstances({
          definition_id: id,
        });
        const instances = response.data.items.filter(
          (instance) => instance.status === 'RUNNING'
        );
        setActiveInstances(instances);

        // Auto-select Active Instances tab if there are active instances
        if (instances.length > 0 && tabValue === 0) {
          setTabValue(1);
        }

        // Only fetch tokens if we're on the Active Instances tab
        if (tabValue === 1) {
          // Fetch tokens for all active instances
          const tokenPromises = instances.map((instance) =>
            apiService.getInstanceTokens(instance.id)
          );
          const tokenResponses = await Promise.all(tokenPromises);
          const allTokens = tokenResponses.flatMap((response) => response.data);
          setTokens(allTokens);
        }
      } catch (error) {
        console.error('Failed to fetch active instances:', error);
      }
    };

    fetchActiveInstances();
    // Set up polling if on active instances tab
    if (tabValue === 1) {
      const interval = setInterval(fetchActiveInstances, 2000);
      return () => clearInterval(interval);
    }
  }, [id, tabValue]);

  useEffect(() => {
    const fetchProcess = async () => {
      if (!id) {
        setError('Process ID is missing');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const response = await apiService.getProcessDefinition(id);

        if (!response.data.bpmn_xml) {
          throw new Error('Process definition has no BPMN XML');
        }

        setProcess({
          name: response.data.name,
          bpmn_xml: response.data.bpmn_xml,
        });
      } catch (error) {
        console.error('Failed to fetch process:', error);
        setError(
          error instanceof Error
            ? error.message
            : 'Failed to load process diagram. Please try again.'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchProcess();
  }, [id]);

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error || !process) {
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
        <Typography color="error" variant="h6">
          {error || 'Failed to load process diagram'}
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link
          color="inherit"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate('/processes');
          }}
        >
          Processes
        </Link>
        <Link
          color="inherit"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate(`/processes/${id}`);
          }}
        >
          {process.name}
        </Link>
        <Typography color="text.primary">Diagram</Typography>
      </Breadcrumbs>

      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          {process.name}
        </Typography>
        <Tabs
          value={tabValue}
          onChange={(_, newValue) => setTabValue(newValue)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Definition" />
          <Tab label={`Active Instances (${activeInstances.length})`} />
        </Tabs>
      </Box>

      <Card>
        <CardContent>
          <Box sx={{ height: '600px' }}>
            <ProcessDiagramViewer
              bpmnXml={process.bpmn_xml}
              key={process.bpmn_xml} // Force re-render when XML changes
              tokens={tabValue === 1 ? tokens : []}
            />
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ProcessDiagram;
