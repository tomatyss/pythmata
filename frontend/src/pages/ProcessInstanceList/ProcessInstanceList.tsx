import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import apiService from '@/services/api';
import { formatDate } from '@/utils/date';
import {
  Box,
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  IconButton,
  Chip,
  CircularProgress,
  Breadcrumbs,
  Link,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  PlayArrow as PlayArrowIcon,
  Pause as PauseIcon,
} from '@mui/icons-material';

interface ProcessInstance {
  id: string;
  definitionId: string;
  definitionName: string;
  status: string;
  startTime: string;
  endTime?: string;
}

const ProcessInstanceList = () => {
  const navigate = useNavigate();
  const { processId } = useParams();
  const [loading, setLoading] = useState(true);
  const [instances, setInstances] = useState<ProcessInstance[]>([]);
  const [processName, setProcessName] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [instancesResponse, processResponse] = await Promise.all([
          apiService.getProcessInstances(processId),
          processId ? apiService.getProcessDefinition(processId) : null,
        ]);

        if (processResponse) {
          setProcessName(processResponse.data.name);
        }

        setInstances(instancesResponse.data.items);
      } catch (error) {
        console.error('Failed to fetch instances:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [processId]);

  const handleViewInstance = (instanceId: string) => {
    navigate(`/processes/${processId}/instances/${instanceId}`);
  };

  const handleSuspendInstance = async (instanceId: string) => {
    try {
      await apiService.suspendProcessInstance(instanceId);
      // Refresh instances list
      const response = await apiService.getProcessInstances(processId);
      setInstances(response.data.items);
    } catch (error) {
      console.error('Failed to suspend instance:', error);
    }
  };

  const handleResumeInstance = async (instanceId: string) => {
    try {
      await apiService.resumeProcessInstance(instanceId);
      // Refresh instances list
      const response = await apiService.getProcessInstances(processId);
      setInstances(response.data.items);
    } catch (error) {
      console.error('Failed to resume instance:', error);
    }
  };

  const filteredInstances = instances.filter(
    (instance) =>
      statusFilter === 'all' || instance.status.toLowerCase() === statusFilter
  );

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
        {processId && (
          <Link
            color="inherit"
            href="#"
            onClick={(e) => {
              e.preventDefault();
              navigate(`/processes/${processId}`);
            }}
          >
            {processName}
          </Link>
        )}
        <Typography color="text.primary">Instances</Typography>
      </Breadcrumbs>

      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 4,
        }}
      >
        <Typography variant="h4">
          Process Instances {processName ? `- ${processName}` : ''}
        </Typography>
        <FormControl sx={{ minWidth: 120 }}>
          <InputLabel>Status</InputLabel>
          <Select
            value={statusFilter}
            label="Status"
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="running">Running</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="suspended">Suspended</MenuItem>
            <MenuItem value="error">Error</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                {!processId && <TableCell>Process</TableCell>}
                <TableCell>Status</TableCell>
                <TableCell>Start Time</TableCell>
                <TableCell>End Time</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredInstances.map((instance) => (
                <TableRow key={instance.id}>
                  <TableCell>{instance.id}</TableCell>
                  {!processId && (
                    <TableCell>{instance.definitionName}</TableCell>
                  )}
                  <TableCell>
                    <Chip
                      label={instance.status}
                      color={
                        instance.status === 'RUNNING'
                          ? 'primary'
                          : instance.status === 'COMPLETED'
                            ? 'success'
                            : instance.status === 'ERROR'
                              ? 'error'
                              : 'default'
                      }
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{formatDate(instance.startTime)}</TableCell>
                  <TableCell>
                    {instance.endTime
                      ? formatDate(instance.endTime)
                      : 'In Progress'}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      onClick={() => handleViewInstance(instance.id)}
                      title="View Instance"
                    >
                      <VisibilityIcon />
                    </IconButton>
                    {instance.status === 'RUNNING' && (
                      <IconButton
                        onClick={() => handleSuspendInstance(instance.id)}
                        title="Suspend Instance"
                      >
                        <PauseIcon />
                      </IconButton>
                    )}
                    {instance.status === 'SUSPENDED' && (
                      <IconButton
                        onClick={() => handleResumeInstance(instance.id)}
                        title="Resume Instance"
                      >
                        <PlayArrowIcon />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {filteredInstances.length === 0 && (
                <TableRow>
                  <TableCell colSpan={processId ? 5 : 6} align="center">
                    <Typography color="textSecondary">
                      No instances found.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </Box>
  );
};

export default ProcessInstanceList;
