/**
 * Project List Page
 * Displays a list of all projects the user has access to
 */

import { useState, useEffect, useCallback } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Grid,
  IconButton,
  Link,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { format } from 'date-fns';

import {
  ROUTES,
  PROJECT_STATUS,
  PROJECT_STATUS_COLORS,
  DEFAULT_PAGE_SIZE,
} from '@/constants';
import PageHeader from '@/components/shared/PageHeader/PageHeader';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import ErrorMessage from '@/components/shared/ErrorMessage';
import useNotification from '@/hooks/useNotification';
import useConfirmDialog from '@/hooks/useConfirmDialog';
import projectService from '@/services/project';
import { Project, ProjectStatus } from '@/types/project';

/**
 * Project List Page Component
 * Displays a list of all projects the user has access to with filtering and pagination
 */
const ProjectList = () => {
  const navigate = useNavigate();
  const { showSuccess, showError } = useNotification();
  const { confirm } = useConfirmDialog();

  // State
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(DEFAULT_PAGE_SIZE);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);

  /**
   * Fetch projects from the API
   */
  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await projectService.getProjects({
        skip: page * rowsPerPage,
        limit: rowsPerPage,
        status: statusFilter || undefined,
      });

      setProjects(response.data);
      setTotalCount(response.data.length); // In a real app, this would come from the paginated response
      setLoading(false);
    } catch (err) {
      setLoading(false);
      setError('Failed to load projects. Please try again.');
      console.error('Error fetching projects:', err);
    }
  }, [page, rowsPerPage, statusFilter]);

  // Load projects on initial render and when filters/pagination change
  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  /**
   * Handle page change
   */
  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  /**
   * Handle rows per page change
   */
  const handleChangeRowsPerPage = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  /**
   * Handle status filter change
   */
  const handleStatusFilterChange = (event: SelectChangeEvent) => {
    setStatusFilter(event.target.value);
    setPage(0);
  };

  /**
   * Handle project deletion
   */
  const handleDeleteProject = async (project: Project) => {
    const confirmed = await confirm({
      title: 'Delete Project',
      message: `Are you sure you want to delete the project "${project.name}"? This action cannot be undone.`,
      confirmText: 'Delete',
      confirmColor: 'error',
    });

    if (confirmed) {
      try {
        await projectService.deleteProject(project.id);
        showSuccess('Project deleted successfully');
        fetchProjects();
      } catch (err) {
        showError('Failed to delete project');
        console.error('Error deleting project:', err);
      }
    }
  };

  /**
   * Render status chip
   */
  const renderStatusChip = (status: string) => {
    const color =
      PROJECT_STATUS_COLORS[status as keyof typeof PROJECT_STATUS_COLORS] ||
      'default';
    return <Chip label={status} color={color} size="small" />;
  };

  if (loading && projects.length === 0) {
    return <LoadingSpinner />;
  }

  return (
    <Container maxWidth="lg">
      <PageHeader
        title="Projects"
        action={
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            component={RouterLink}
            to={ROUTES.NEW_PROJECT}
          >
            New Project
          </Button>
        }
      />

      {error && <ErrorMessage message={error} />}

      <Paper sx={{ mt: 3, p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
          <Select
            value={statusFilter}
            onChange={handleStatusFilterChange}
            displayEmpty
            size="small"
            sx={{ minWidth: 150 }}
          >
            <MenuItem value="">All Statuses</MenuItem>
            {Object.values(PROJECT_STATUS).map((status) => (
              <MenuItem key={status} value={status}>
                {status}
              </MenuItem>
            ))}
          </Select>
        </Box>

        {projects.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body1" color="textSecondary">
              No projects found. Create your first project to get started.
            </Typography>
            <Button
              variant="contained"
              color="primary"
              startIcon={<AddIcon />}
              component={RouterLink}
              to={ROUTES.NEW_PROJECT}
              sx={{ mt: 2 }}
            >
              Create Project
            </Button>
          </Box>
        ) : (
          <>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Owner</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Members</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {projects.map((project) => (
                    <TableRow key={project.id} hover>
                      <TableCell>
                        <Link
                          component={RouterLink}
                          to={ROUTES.PROJECT_DETAILS(project.id)}
                          underline="hover"
                          color="primary"
                          fontWeight="medium"
                        >
                          {project.name}
                        </Link>
                        {project.description && (
                          <Typography
                            variant="body2"
                            color="textSecondary"
                            noWrap
                          >
                            {project.description.length > 60
                              ? `${project.description.substring(0, 60)}...`
                              : project.description}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>{renderStatusChip(project.status)}</TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {project.owner.full_name || project.owner.email}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {format(new Date(project.createdAt), 'MMM d, yyyy')}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {project.members.length}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={1}>
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() =>
                              navigate(ROUTES.PROJECT_DETAILS(project.id))
                            }
                            title="View project"
                          >
                            <VisibilityIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() =>
                              navigate(
                                `${ROUTES.PROJECT_DETAILS(project.id)}?edit=true`
                              )
                            }
                            title="Edit project"
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteProject(project)}
                            title="Delete project"
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <TablePagination
              rowsPerPageOptions={[5, 10, 25]}
              component="div"
              count={totalCount}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
            />
          </>
        )}
      </Paper>

      <Grid container spacing={3} sx={{ mt: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Draft Projects
              </Typography>
              <Typography variant="h3" color="primary">
                {
                  projects.filter((p) => p.status === ProjectStatus.DRAFT)
                    .length
                }
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Active Projects
              </Typography>
              <Typography variant="h3" color="primary">
                {
                  projects.filter((p) => p.status === ProjectStatus.ACTIVE)
                    .length
                }
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Completed Projects
              </Typography>
              <Typography variant="h3" color="primary">
                {
                  projects.filter((p) => p.status === ProjectStatus.COMPLETED)
                    .length
                }
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default ProjectList;
