import { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import apiService from '@/services/api';
import ProcessDiagramViewer from '@/components/shared/ProcessDiagramViewer';
import { useProcessTokens } from '@/hooks/useProcessTokens';
import { ProcessInstance, ProcessStatus } from '@/types/process';
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Checkbox,
  FormControlLabel,
} from '@mui/material';

interface ProcessDetails {
  name: string;
  bpmnXml: string;
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
  const [showFinishedInstances, setShowFinishedInstances] = useState(false);
  const navigate = useNavigate();

  // Get IDs of running instances - memoize to prevent unnecessary recalculations
  const runningInstanceIds = useMemo(
    () =>
      activeInstances
        .filter((instance) => instance.status === ProcessStatus.RUNNING)
        .map((instance) => instance.id),
    [activeInstances]
  );

  // Use the useProcessTokens hook with all running instance IDs
  const { tokens: allTokens, error: tokensError } = useProcessTokens({
    instanceId: runningInstanceIds,
    // Only enable when on Active Instances tab and there are running instances
    enabled: tabValue === 1 && runningInstanceIds.length > 0,
    pollingInterval: 2000,
  });

  // Fetch active instances
  const fetchActiveInstances = useCallback(async (): Promise<void> => {
    if (!id) return;

    try {
      const response = await apiService.getProcessInstances({
        definitionId: id,
        page: 1,
        pageSize: 100,
      });

      if (!response.data?.items) {
        throw new Error('Invalid API response format');
      }

      const instances = response.data.items.filter(
        (instance) =>
          showFinishedInstances || instance?.status === ProcessStatus.RUNNING
      );

      setActiveInstances(instances);
    } catch (error) {
      console.error('Failed to fetch active instances:', error);
    }
  }, [id, showFinishedInstances]);

  // Handle auto-select of Active Instances tab - only on initial load
  useEffect(() => {
    const hasInstances = activeInstances.length > 0;
    const isInitialTab = tabValue === 0;

    if (hasInstances && isInitialTab) {
      // Use a timeout to ensure this happens after other state updates
      const timeoutId = setTimeout(() => {
        setTabValue(1);
      }, 0);

      return () => clearTimeout(timeoutId);
    }
    return undefined;
  }, [activeInstances.length]); // Only depend on instances length, not tabValue

  // Setup polling for active instances
  useEffect(() => {
    // Initial fetch
    fetchActiveInstances();

    // Only poll when on the Active Instances tab
    if (tabValue === 1) {
      const interval = setInterval(fetchActiveInstances, 2000);
      return () => clearInterval(interval);
    }
    return undefined;
  }, [tabValue, fetchActiveInstances, tabValue]);

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

        if (!response.data.bpmnXml) {
          throw new Error('Process definition has no BPMN XML');
        }

        setProcess({
          name: response.data.name,
          bpmnXml: response.data.bpmnXml,
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

      {tabValue === 1 && (
        <>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ height: '600px' }}>
                <ProcessDiagramViewer
                  bpmnXml={process.bpmnXml}
                  key={process.bpmnXml}
                  tokens={tabValue === 1 ? allTokens : []}
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

          <Box sx={{ mb: 2 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={showFinishedInstances}
                  onChange={(e) => setShowFinishedInstances(e.target.checked)}
                />
              }
              label="Show Finished Instances"
            />
          </Box>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Instance ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Start Time</TableCell>
                  <TableCell>Last Updated</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {activeInstances.map((instance) => (
                  <TableRow
                    key={instance.id}
                    hover
                    sx={{
                      backgroundColor:
                        instance.status === ProcessStatus.RUNNING
                          ? 'rgba(0, 128, 0, 0.1)'
                          : undefined,
                    }}
                  >
                    <TableCell>
                      <RouterLink
                        to={`/processes/${id}/instances/${instance.id}`}
                        style={{ color: 'inherit', textDecoration: 'none' }}
                      >
                        {instance.id}
                      </RouterLink>
                    </TableCell>
                    <TableCell>{instance.status}</TableCell>
                    <TableCell>
                      {instance.startTime
                        ? new Date(instance.startTime).toLocaleString()
                        : 'N/A'}
                    </TableCell>
                    <TableCell>
                      {instance.updatedAt
                        ? new Date(instance.updatedAt).toLocaleString()
                        : 'N/A'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}
    </Box>
  );
};

export default ProcessDiagram;
