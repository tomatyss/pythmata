import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import apiService from '@/services/api';
import {
  Box,
  Button,
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
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayArrowIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import ProcessVariablesDialog, {
  ProcessVariables,
} from '@/components/shared/ProcessVariablesDialog/ProcessVariablesDialog';

interface Process {
  id: string;
  name: string;
  version: number;
  activeInstances: number;
  totalInstances: number;
  lastModified: string;
}

const ProcessList = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [processes, setProcesses] = useState<Process[]>([]);
  const [selectedProcessId, setSelectedProcessId] = useState<string | null>(
    null
  );
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    const fetchProcesses = async () => {
      try {
        const response = await apiService.getProcessDefinitions();
        setProcesses(
          response.data.items.map((process) => ({
            id: process.id,
            name: process.name,
            version: process.version,
            activeInstances: 0,
            totalInstances: 0,
            lastModified: process.updatedAt,
          }))
        );
      } catch {
        alert('Failed to load processes. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchProcesses();
  }, []);

  const handleStartProcess = (processId: string) => {
    setSelectedProcessId(processId);
    setDialogOpen(true);
  };

  const handleStartProcessSubmit = async (variables: ProcessVariables) => {
    if (!selectedProcessId) return;

    try {
      const response = await apiService.startProcessInstance({
        definitionId: selectedProcessId,
        variables,
      });
      navigate(`/instances/${response.data.id}`);
    } catch {
      alert('Failed to start process. Please try again.');
    }
  };

  const handleEditProcess = (processId: string) => {
    navigate(`/processes/${processId}`);
  };

  const handleDeleteProcess = (_processId: string) => {
    // TODO: Implement process deletion
    alert('Process deletion functionality not yet implemented');
  };

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
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 4,
        }}
      >
        <Typography variant="h4">Process Definitions</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/processes/new')}
        >
          New Process
        </Button>
      </Box>

      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Version</TableCell>
                <TableCell>Active Instances</TableCell>
                <TableCell>Total Instances</TableCell>
                <TableCell>Last Modified</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {processes.map((process) => (
                <TableRow key={process.id}>
                  <TableCell>{process.name}</TableCell>
                  <TableCell>
                    <Chip
                      label={`v${process.version}`}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>{process.activeInstances}</TableCell>
                  <TableCell>{process.totalInstances}</TableCell>
                  <TableCell>
                    {new Date(process.lastModified).toLocaleString()}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      color="primary"
                      onClick={() => handleStartProcess(process.id)}
                      title="Start Process"
                    >
                      <PlayArrowIcon />
                    </IconButton>
                    <IconButton
                      color="primary"
                      onClick={() => handleEditProcess(process.id)}
                      title="Edit Process"
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      color="error"
                      onClick={() => handleDeleteProcess(process.id)}
                      title="Delete Process"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {processes.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <Typography color="textSecondary">
                      No processes found. Create a new process to get started.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <ProcessVariablesDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleStartProcessSubmit}
      />
    </Box>
  );
};

export default ProcessList;
