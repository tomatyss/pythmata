/**
 * Project Processes Page
 * Displays and manages the processes associated with a project
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemSecondaryAction,
  ListItemText,
  Paper,
  TextField,
  Typography,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  ArrowBack as ArrowBackIcon,
  Visibility as VisibilityIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayArrowIcon,
  AccountTree as AccountTreeIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';

import { ROUTES, STATUS_COLORS } from '@/constants';
import PageHeader from '@/components/shared/PageHeader/PageHeader';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import ErrorMessage from '@/components/shared/ErrorMessage';
import useNotification from '@/hooks/useNotification';
import useConfirmDialog from '@/hooks/useConfirmDialog';
import projectService from '@/services/project';
import apiService from '@/services/api';
import { Project } from '@/types/project';
import { ProcessDefinition } from '@/types/process';

/**
 * Project Processes Page Component
 * Displays and manages the processes associated with a project
 */
const ProjectProcesses = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showSuccess, showError } = useNotification();
  const { confirm } = useConfirmDialog();

  // State
  const [project, setProject] = useState<Project | null>(null);
  const [processes, setProcesses] = useState<ProcessDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newProcessName, setNewProcessName] = useState('');
  const [newProcessDescription, setNewProcessDescription] = useState('');

  /**
   * Fetch project details from the API
   */
  const fetchProject = useCallback(async () => {
    if (!id) return;

    try {
      setLoading(true);
      setError(null);

      const response = await projectService.getProject(id);
      setProject(response.data);
      setLoading(false);
    } catch (err) {
      setLoading(false);
      setError('Failed to load project details. Please try again.');
      console.error('Error fetching project:', err);
    }
  }, [id]);

  /**
   * Fetch project processes from the API
   */
  const fetchProcesses = useCallback(async () => {
    if (!id) return;

    try {
      // This would be a call to get processes for a specific project
      // For now, we'll simulate it by filtering all processes
      const response = await apiService.getProcessDefinitions();
      const projectProcesses = response.data.items.filter(
        (process) => process.projectId === id
      );
      setProcesses(projectProcesses);
    } catch (err) {
      console.error('Error fetching project processes:', err);
    }
  }, [id]);

  // Load project and processes on initial render
  useEffect(() => {
    fetchProject();
    fetchProcesses();
  }, [id, fetchProject, fetchProcesses]);

  /**
   * Handle creating a new process
   */
  const handleCreateProcess = async () => {
    if (!id || !newProcessName) return;

    try {
      setLoading(true);

      // Create a new process definition
      await apiService.createProcessDefinition({
        name: newProcessName,
        description: newProcessDescription,
        bpmnXml: '<xml></xml>', // Empty XML for now
        projectId: id,
      });

      showSuccess('Process created successfully');
      setCreateDialogOpen(false);
      setNewProcessName('');
      setNewProcessDescription('');
      fetchProcesses();
    } catch (err) {
      showError('Failed to create process');
      console.error('Error creating process:', err);
      setLoading(false);
    }
  };

  /**
   * Handle deleting a process
   */
  const handleDeleteProcess = async (process: ProcessDefinition) => {
    const confirmed = await confirm({
      title: 'Delete Process',
      message: `Are you sure you want to delete the process "${process.name}"? This action cannot be undone.`,
      confirmText: 'Delete',
      confirmColor: 'error',
    });

    if (confirmed) {
      try {
        setLoading(true);
        await apiService.deleteProcessDefinition(process.id);
        showSuccess('Process deleted successfully');
        fetchProcesses();
      } catch (err) {
        showError('Failed to delete process');
        console.error('Error deleting process:', err);
        setLoading(false);
      }
    }
  };

  /**
   * Handle generating a process from description
   */
  const handleGenerateFromDescription = () => {
    if (!project?.currentDescription) {
      showError('No current description available');
      return;
    }

    // Navigate to process creation with description context
    // This would be implemented in a real application
    showSuccess('Process generation would be implemented here');
  };

  /**
   * Render status chip
   */
  const renderStatusChip = (status: string) => {
    const color =
      STATUS_COLORS[status as keyof typeof STATUS_COLORS] || 'default';
    return <Chip label={status} color={color} size="small" />;
  };

  if (loading && !project) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage message={error} />;
  }

  if (!project) {
    return <ErrorMessage message="Project not found" />;
  }

  return (
    <Container maxWidth="lg">
      <PageHeader
        title="Project Processes"
        breadcrumbs={[
          { label: 'Projects', href: ROUTES.PROJECTS },
          { label: project.name, href: ROUTES.PROJECT_DETAILS(project.id) },
          { label: 'Processes' },
        ]}
        action={
          <Box sx={{ display: 'flex', gap: 2 }}>
            {project.currentDescription && (
              <Button
                variant="outlined"
                color="primary"
                startIcon={<AccountTreeIcon />}
                onClick={handleGenerateFromDescription}
              >
                Generate from Description
              </Button>
            )}
            <Button
              variant="contained"
              color="primary"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
            >
              Create Process
            </Button>
          </Box>
        }
      />

      <Paper sx={{ p: 2, mb: 3 }}>
        <Button
          component={RouterLink}
          to={ROUTES.PROJECT_DETAILS(project.id)}
          startIcon={<ArrowBackIcon />}
        >
          Back to Project
        </Button>
      </Paper>

      <Card>
        <CardHeader
          title="Project Processes"
          subheader={`${processes.length} processes in this project`}
        />
        <Divider />
        <CardContent>
          {processes.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="textSecondary">
                No processes in this project yet.
              </Typography>
              <Typography
                variant="body2"
                color="textSecondary"
                sx={{ mt: 1, mb: 2 }}
              >
                Create a new process or generate one from the project
                description.
              </Typography>
              <Grid container spacing={2} justifyContent="center">
                <Grid item>
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={() => setCreateDialogOpen(true)}
                  >
                    Create Process
                  </Button>
                </Grid>
                {project.currentDescription && (
                  <Grid item>
                    <Button
                      variant="outlined"
                      color="primary"
                      startIcon={<AccountTreeIcon />}
                      onClick={handleGenerateFromDescription}
                    >
                      Generate from Description
                    </Button>
                  </Grid>
                )}
              </Grid>
            </Box>
          ) : (
            <List>
              {processes.map((process) => (
                <ListItem key={process.id} divider>
                  <ListItemIcon>
                    <AccountTreeIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Typography variant="subtitle1">
                        {process.name}
                      </Typography>
                    }
                    secondary={
                      <>
                        <Typography
                          component="span"
                          variant="body2"
                          color="textSecondary"
                        >
                          {process.description || 'No description'}
                        </Typography>
                        <Box
                          sx={{ mt: 1, display: 'flex', alignItems: 'center' }}
                        >
                          <Typography
                            component="span"
                            variant="body2"
                            color="textSecondary"
                            sx={{ mr: 2 }}
                          >
                            Created:{' '}
                            {format(new Date(process.createdAt), 'MMM d, yyyy')}
                          </Typography>
                          {process.status && renderStatusChip(process.status)}
                        </Box>
                      </>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Tooltip title="View Process">
                      <IconButton
                        edge="end"
                        aria-label="view"
                        onClick={() =>
                          navigate(ROUTES.PROCESS_DETAILS(process.id))
                        }
                        sx={{ mr: 1 }}
                      >
                        <VisibilityIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit Process">
                      <IconButton
                        edge="end"
                        aria-label="edit"
                        onClick={() =>
                          navigate(ROUTES.PROCESS_DETAILS(process.id))
                        }
                        sx={{ mr: 1 }}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Run Process">
                      <IconButton
                        edge="end"
                        aria-label="run"
                        onClick={() =>
                          navigate(`/processes/${process.id}/instances`)
                        }
                        sx={{ mr: 1 }}
                      >
                        <PlayArrowIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete Process">
                      <IconButton
                        edge="end"
                        aria-label="delete"
                        onClick={() => handleDeleteProcess(process)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </CardContent>
      </Card>

      {/* Create Process Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Process</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              fullWidth
              label="Process Name"
              value={newProcessName}
              onChange={(e) => setNewProcessName(e.target.value)}
              margin="normal"
              variant="outlined"
              required
            />
            <TextField
              fullWidth
              label="Description"
              value={newProcessDescription}
              onChange={(e) => setNewProcessDescription(e.target.value)}
              margin="normal"
              variant="outlined"
              multiline
              rows={4}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateProcess}
            color="primary"
            variant="contained"
            disabled={!newProcessName}
          >
            Create Process
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ProjectProcesses;
