import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiService from '@/services/api';
import ProcessDiagramViewer from '@/components/shared/ProcessDiagramViewer';
import { useProcessTokens } from '@/hooks/useProcessTokens';
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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';

interface ProcessDetails {
  name: string;
  bpmn_xml: string;
}

interface ProcessInstance {
  id: string;
  status: string;
  definitionId: string;
  definitionName: string;
  startTime: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * ProcessDiagram component displays a BPMN process diagram with active instance visualization
 * Features:
 * - Shows process definition diagram
 * - Displays active process instances
 * - Visualizes token positions for selected instances
 * - Auto-refreshes instance and token data
 *
 * @returns React component that renders the process diagram viewer with instance selection
 */
const ProcessDiagram = (): React.ReactElement => {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [process, setProcess] = useState<ProcessDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [activeInstances, setActiveInstances] = useState<ProcessInstance[]>([]);
  const [selectedInstanceId, setSelectedInstanceId] = useState<string | ''>('');
  const navigate = useNavigate();

  // Use the useProcessTokens hook for the selected instance
  const { tokens = [], error: tokensError } = useProcessTokens({
    instanceId: selectedInstanceId || '',
    enabled: tabValue === 1 && !!selectedInstanceId,
    pollingInterval: 2000,
  });

  // Fetch active instances
  useEffect(() => {
    const fetchActiveInstances = async (): Promise<void> => {
      if (!id) return undefined;

      try {
        let allInstances: ProcessInstance[] = [];
        let currentPage = 1;
        let hasMorePages = true;

        // Fetch all pages of instances
        while (hasMorePages) {
          const response = await apiService.getProcessInstances({
            definition_id: id,
            page: currentPage,
            page_size: 100, // Fetch more instances per page
          });

          if (!response.data?.items || !response.data.totalPages) {
            throw new Error('Invalid API response format');
          }

          const runningInstances = response.data.items.filter(
            (instance) => instance?.status === 'RUNNING'
          ) as ProcessInstance[];
          allInstances = [...allInstances, ...runningInstances];

          // Check if there are more pages
          hasMorePages = currentPage < response.data.totalPages;
          currentPage++;
        }

        setActiveInstances(allInstances);

        // Auto-select Active Instances tab if there are active instances
        if (allInstances.length > 0 && tabValue === 0) {
          setTabValue(1);
          // Auto-select first instance if none selected
          if (!selectedInstanceId) {
            setSelectedInstanceId(allInstances[0].id);
          }
        }
      } catch (error) {
        console.error('Failed to fetch active instances:', error);
      }
    };

    fetchActiveInstances();
    // Set up polling for active instances list
    if (tabValue === 1) {
      const interval = setInterval(fetchActiveInstances, 2000);
      return () => clearInterval(interval);
    }
  }, [id, tabValue, selectedInstanceId]);

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

  // Reset selected instance when changing tabs
  useEffect(() => {
    if (tabValue === 0) {
      setSelectedInstanceId('');
    }
  }, [tabValue]);

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

      {tabValue === 1 && activeInstances.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <FormControl fullWidth>
            <InputLabel id="instance-select-label">Select Instance</InputLabel>
            <Select
              labelId="instance-select-label"
              value={selectedInstanceId}
              label="Select Instance"
              onChange={(e) => setSelectedInstanceId(e.target.value)}
            >
              {activeInstances.map((instance) => (
                <MenuItem key={instance.id} value={instance.id}>
                  Instance {instance.id}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      )}

      <Card>
        <CardContent>
          <Box sx={{ height: '600px' }}>
            <ProcessDiagramViewer
              bpmnXml={process.bpmn_xml}
              key={process.bpmn_xml} // Force re-render when XML changes
              tokens={tabValue === 1 && selectedInstanceId ? tokens : []}
            />
            {tokensError && (
              <Typography color="error" sx={{ mt: 2 }}>
                Error loading tokens:{' '}
                {tokensError instanceof Error
                  ? tokensError.message
                  : 'Failed to load tokens'}
              </Typography>
            )}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ProcessDiagram;
