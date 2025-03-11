import { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
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
  Alert,
  Button,
  Tooltip,
} from '@mui/material';
import { formatDate } from '@/utils/dateUtils';
import { Refresh as RefreshIcon } from '@mui/icons-material';

interface ProcessDetails {
  name: string;
  bpmnXml: string;
  version?: number;
  updatedAt?: string;
}

const POLL_INTERVAL = 5000; // 5 seconds

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
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [process, setProcess] = useState<ProcessDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [activeInstances, setActiveInstances] = useState<ProcessInstance[]>([]);
  const [showFinishedInstances, setShowFinishedInstances] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Get IDs of running instances - memoize to prevent unnecessary recalculations
  const runningInstanceIds = useMemo(
    () =>
      activeInstances
        .filter((instance) => instance.status === ProcessStatus.RUNNING)
        .map((instance) => instance.id),
    [activeInstances]
  );

  // Use the useProcessTokens hook with all running instance IDs
  const {
    tokens: allTokens,
    error: tokensError,
    refetch: refetchTokens,
  } = useProcessTokens({
    instanceId: runningInstanceIds,
    // Only enable when on Active Instances tab and there are running instances
    enabled: tabValue === 1 && runningInstanceIds.length > 0,
    pollingInterval: POLL_INTERVAL,
  });

  // Fetch active instances
  const fetchActiveInstances = useCallback(
    async (showRefreshing = false): Promise<void> => {
      if (!id) return;

      try {
        if (showRefreshing) setRefreshing(true);

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
        // We don't set an error state here to avoid disrupting the UI for a failed refresh
      } finally {
        if (showRefreshing) setRefreshing(false);
      }
    },
    [id, showFinishedInstances]
  );

  // Manual refresh handler
  const handleRefresh = useCallback(() => {
    fetchActiveInstances(true);
    if (tabValue === 1 && runningInstanceIds.length > 0) {
      refetchTokens();
    }
  }, [fetchActiveInstances, refetchTokens, tabValue, runningInstanceIds]);

  // Setup polling for active instances
  useEffect(() => {
    // Initial fetch
    fetchActiveInstances();

    // Only poll when on the Active Instances tab
    if (tabValue === 1) {
      const interval = setInterval(() => fetchActiveInstances(), POLL_INTERVAL);
      return () => clearInterval(interval);
    }
    return undefined;
  }, [tabValue, fetchActiveInstances]);

  // Fetch process details
  const fetchProcessDetails = useCallback(async () => {
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
        version: response.data.version,
        updatedAt: response.data.updatedAt,
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
  }, [id]);

  useEffect(() => {
    fetchProcessDetails();
  }, [fetchProcessDetails]);

  // Render loading state
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

  // Render error state
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
        <Alert severity="error" sx={{ maxWidth: '600px' }}>
          {error || 'Failed to load process diagram'}
        </Alert>
        <Button variant="contained" onClick={fetchProcessDetails}>
          Try Again
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Breadcrumbs Navigation */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link
          component={RouterLink}
          to="/processes"
          color="inherit"
          underline="hover"
        >
          Processes
        </Link>
        <Link
          component={RouterLink}
          to={`/processes/${id}`}
          color="inherit"
          underline="hover"
        >
          {process.name}
        </Link>
        <Typography color="text.primary">Diagram</Typography>
      </Breadcrumbs>

      {/* Page Header */}
      <Box
        sx={{
          mb: 3,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="h4" gutterBottom>
            {process.name}
            {process.version && (
              <Typography component="span" variant="subtitle1" sx={{ ml: 2 }}>
                v{process.version}
              </Typography>
            )}
          </Typography>
          {process.updatedAt && (
            <Typography variant="body2" color="text.secondary">
              Last updated: {formatDate(process.updatedAt)}
            </Typography>
          )}
        </Box>

        <Tooltip title="Refresh data">
          <Button
            variant="outlined"
            size="small"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={refreshing}
          >
            Refresh
          </Button>
        </Tooltip>
      </Box>

      {/* Tab Navigation */}
      <Tabs
        value={tabValue}
        onChange={(_, newValue) => setTabValue(newValue)}
        sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}
      >
        <Tab label="Definition" />
        <Tab label={`Active Instances (${activeInstances.length})`} />
      </Tabs>

      {/* Definition Tab Content */}
      {tabValue === 0 && (
        <Card elevation={2}>
          <CardContent>
            <Box sx={{ height: '600px' }}>
              <ProcessDiagramViewer
                bpmnXml={process.bpmnXml}
                key={`definition-${process.bpmnXml.length}`}
                tokens={[]} // No tokens needed for definition view
              />
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Active Instances Tab Content */}
      {tabValue === 1 && (
        <>
          <Card elevation={2} sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ height: '600px' }}>
                <ProcessDiagramViewer
                  bpmnXml={process.bpmnXml}
                  key={`instances-${process.bpmnXml.length}-${allTokens.length}`}
                  tokens={allTokens}
                />
                {tokensError && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    Error loading tokens:{' '}
                    {tokensError instanceof Error
                      ? tokensError.message
                      : 'Failed to load tokens'}
                  </Alert>
                )}
              </Box>
            </CardContent>
          </Card>

          <Box
            sx={{
              mb: 2,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <FormControlLabel
              control={
                <Checkbox
                  checked={showFinishedInstances}
                  onChange={(e) => setShowFinishedInstances(e.target.checked)}
                />
              }
              label="Show Finished Instances"
            />

            <Typography variant="body2" color="text.secondary">
              Showing {activeInstances.length} instances
              {refreshing && <CircularProgress size={16} sx={{ ml: 1 }} />}
            </Typography>
          </Box>

          {/* Instances Table */}
          {activeInstances.length > 0 ? (
            <TableContainer component={Paper} elevation={2}>
              <Table size="small">
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
                            ? 'rgba(25, 118, 210, 0.08)'
                            : instance.status === ProcessStatus.COMPLETED
                              ? 'rgba(46, 125, 50, 0.08)'
                              : instance.status === ProcessStatus.ERROR
                                ? 'rgba(211, 47, 47, 0.08)'
                                : instance.status === ProcessStatus.SUSPENDED
                                  ? 'rgba(237, 108, 2, 0.08)'
                                  : undefined,
                      }}
                    >
                      <TableCell>
                        <RouterLink
                          to={`/processes/${id}/instances/${instance.id}`}
                          style={{
                            color: 'inherit',
                            textDecoration: 'none',
                            fontWeight: 'bold',
                          }}
                        >
                          {instance.id}
                        </RouterLink>
                      </TableCell>
                      <TableCell>
                        <Tooltip title={instance.status}>
                          <Typography
                            variant="body2"
                            component="span"
                            sx={{
                              px: 1.5,
                              py: 0.5,
                              borderRadius: 1,
                              fontWeight: 'medium',
                              backgroundColor:
                                instance.status === ProcessStatus.RUNNING
                                  ? 'primary.light'
                                  : instance.status === ProcessStatus.COMPLETED
                                    ? 'success.light'
                                    : instance.status === ProcessStatus.ERROR
                                      ? 'error.light'
                                      : instance.status ===
                                          ProcessStatus.SUSPENDED
                                        ? 'warning.light'
                                        : 'grey.100',
                              color:
                                instance.status === ProcessStatus.RUNNING
                                  ? 'primary.contrastText'
                                  : instance.status === ProcessStatus.COMPLETED
                                    ? 'success.contrastText'
                                    : instance.status === ProcessStatus.ERROR
                                      ? 'error.contrastText'
                                      : instance.status ===
                                          ProcessStatus.SUSPENDED
                                        ? 'warning.contrastText'
                                        : 'text.primary',
                            }}
                          >
                            {instance.status}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        {instance.startTime
                          ? formatDate(instance.startTime)
                          : 'N/A'}
                      </TableCell>
                      <TableCell>
                        {instance.updatedAt
                          ? formatDate(instance.updatedAt)
                          : 'N/A'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Alert severity="info">
              No {showFinishedInstances ? '' : 'active'} instances found for
              this process.
            </Alert>
          )}
        </>
      )}
    </Box>
  );
};

export default ProcessDiagram;
