/**
 * Project Details Page
 * Displays detailed information about a project and allows editing
 */

import { useState, useEffect, useCallback } from 'react';
import {
  useParams,
  useNavigate,
  useSearchParams,
  Link as RouterLink,
} from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Container,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Tab,
  Tabs,
  TextField,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
} from '@mui/material';
import {
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Person as PersonIcon,
  Description as DescriptionIcon,
  AccountTree as AccountTreeIcon,
  CalendarToday as CalendarIcon,
  Group as GroupIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';

import { ROUTES, PROJECT_STATUS, PROJECT_STATUS_COLORS } from '@/constants';
import PageHeader from '@/components/shared/PageHeader/PageHeader';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import ErrorMessage from '@/components/shared/ErrorMessage';
import useNotification from '@/hooks/useNotification';
import projectService from '@/services/project';
import { Project, ProjectUpdate } from '@/types/project';

/**
 * Project Details Page Component
 * Displays detailed information about a project and allows editing
 */
const ProjectDetails = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { showSuccess, showError } = useNotification();

  // State
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(
    searchParams.get('edit') === 'true'
  );
  const [activeTab, setActiveTab] = useState(0);

  // Form state
  const [formData, setFormData] = useState<ProjectUpdate>({
    name: '',
    description: '',
    status: '',
  });

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
      setFormData({
        name: response.data.name,
        description: response.data.description || '',
        status: response.data.status,
      });
      setLoading(false);
    } catch (err) {
      setLoading(false);
      setError('Failed to load project details. Please try again.');
      console.error('Error fetching project:', err);
    }
  }, [id]);

  // Load project on initial render
  useEffect(() => {
    fetchProject();
  }, [id, fetchProject]);

  /**
   * Handle tab change
   */
  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  /**
   * Handle form field change
   */
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | { name?: string; value: unknown }>
  ) => {
    const { name, value } = e.target;
    if (name) {
      setFormData((prev) => ({
        ...prev,
        [name]: value,
      }));
    }
  };

  /**
   * Handle select change
   */
  const handleSelectChange = (e: SelectChangeEvent) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;

    try {
      setLoading(true);
      await projectService.updateProject(id, formData);
      showSuccess('Project updated successfully');
      setIsEditing(false);
      fetchProject();
    } catch (err) {
      showError('Failed to update project');
      console.error('Error updating project:', err);
      setLoading(false);
    }
  };

  /**
   * Cancel editing
   */
  const handleCancel = () => {
    if (project) {
      setFormData({
        name: project.name,
        description: project.description || '',
        status: project.status,
      });
    }
    setIsEditing(false);
  };

  /**
   * Navigate to different project sections
   */
  const navigateToSection = (section: string) => {
    if (!id) return;

    switch (section) {
      case 'members':
        navigate(ROUTES.PROJECT_MEMBERS(id));
        break;
      case 'descriptions':
        navigate(ROUTES.PROJECT_DESCRIPTIONS(id));
        break;
      case 'processes':
        navigate(ROUTES.PROJECT_PROCESSES(id));
        break;
      default:
        break;
    }
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
        title={isEditing ? 'Edit Project' : project.name}
        breadcrumbs={[
          { label: 'Projects', href: ROUTES.PROJECTS },
          { label: project.name },
        ]}
        action={
          !isEditing ? (
            <Button
              variant="contained"
              color="primary"
              startIcon={<EditIcon />}
              onClick={() => setIsEditing(true)}
            >
              Edit Project
            </Button>
          ) : null
        }
      />

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
        >
          <Tab label="Overview" />
          <Tab label="Members" onClick={() => navigateToSection('members')} />
          <Tab
            label="Descriptions"
            onClick={() => navigateToSection('descriptions')}
          />
          <Tab
            label="Processes"
            onClick={() => navigateToSection('processes')}
          />
        </Tabs>
      </Paper>

      {isEditing ? (
        <Card>
          <CardContent>
            <form onSubmit={handleSubmit}>
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    id="name"
                    name="name"
                    label="Project Name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                  />
                </Grid>

                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    id="description"
                    name="description"
                    label="Description"
                    multiline
                    rows={4}
                    value={formData.description}
                    onChange={handleChange}
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <FormControl fullWidth>
                    <InputLabel id="status-label">Status</InputLabel>
                    <Select
                      labelId="status-label"
                      id="status"
                      name="status"
                      value={formData.status}
                      onChange={handleSelectChange}
                      label="Status"
                    >
                      {Object.values(PROJECT_STATUS).map((status) => (
                        <MenuItem key={status} value={status}>
                          {status}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12}>
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'flex-end',
                      gap: 2,
                      mt: 2,
                    }}
                  >
                    <Button
                      variant="outlined"
                      color="inherit"
                      startIcon={<CancelIcon />}
                      onClick={handleCancel}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      variant="contained"
                      color="primary"
                      startIcon={<SaveIcon />}
                    >
                      Save Changes
                    </Button>
                  </Box>
                </Grid>
              </Grid>
            </form>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardHeader
                title="Project Details"
                action={
                  <Chip
                    label={project.status}
                    color={
                      PROJECT_STATUS_COLORS[
                        project.status as keyof typeof PROJECT_STATUS_COLORS
                      ]
                    }
                  />
                }
              />
              <Divider />
              <CardContent>
                {project.description ? (
                  <Typography variant="body1" paragraph>
                    {project.description}
                  </Typography>
                ) : (
                  <Typography variant="body2" color="textSecondary" paragraph>
                    No description provided.
                  </Typography>
                )}

                <Grid container spacing={2} sx={{ mt: 2 }}>
                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <CalendarIcon sx={{ mr: 1, color: 'text.secondary' }} />
                      <Typography variant="body2" color="textSecondary">
                        Created on{' '}
                        {format(new Date(project.createdAt), 'MMMM d, yyyy')}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <PersonIcon sx={{ mr: 1, color: 'text.secondary' }} />
                      <Typography variant="body2" color="textSecondary">
                        Owner: {project.owner.full_name || project.owner.email}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <GroupIcon sx={{ mr: 1, color: 'text.secondary' }} />
                      <Typography variant="body2" color="textSecondary">
                        {project.members.length} team members
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <AccountTreeIcon
                        sx={{ mr: 1, color: 'text.secondary' }}
                      />
                      <Typography variant="body2" color="textSecondary">
                        {project.processCount || 0} processes
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            {project.currentDescription && (
              <Card sx={{ mt: 3 }}>
                <CardHeader
                  title="Current Description"
                  subheader={`Version ${project.currentDescription.version}`}
                  action={
                    <Button
                      component={RouterLink}
                      to={ROUTES.PROJECT_DESCRIPTIONS(project.id)}
                      size="small"
                    >
                      View All
                    </Button>
                  }
                />
                <Divider />
                <CardContent>
                  <Typography variant="body1" paragraph>
                    {project.currentDescription.content.length > 300
                      ? `${project.currentDescription.content.substring(0, 300)}...`
                      : project.currentDescription.content}
                  </Typography>
                  {project.currentDescription.content.length > 300 && (
                    <Button
                      component={RouterLink}
                      to={ROUTES.PROJECT_DESCRIPTION(
                        project.id,
                        project.currentDescription.id
                      )}
                      size="small"
                    >
                      Read More
                    </Button>
                  )}
                  {project.currentDescription.tags.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      {project.currentDescription.tags.map((tag) => (
                        <Chip
                          key={tag.id}
                          label={tag.name}
                          size="small"
                          sx={{ mr: 1, mb: 1, bgcolor: tag.color }}
                        />
                      ))}
                    </Box>
                  )}
                </CardContent>
              </Card>
            )}
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardHeader title="Quick Actions" />
              <Divider />
              <List>
                <ListItem
                  component="div"
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigateToSection('members')}
                >
                  <ListItemIcon>
                    <GroupIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Manage Team Members"
                    secondary={`${project.members.length} members`}
                  />
                </ListItem>
                <ListItem
                  component="div"
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigateToSection('descriptions')}
                >
                  <ListItemIcon>
                    <DescriptionIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Manage Descriptions"
                    secondary={
                      project.descriptions?.length
                        ? `${project.descriptions.length} versions`
                        : 'No descriptions yet'
                    }
                  />
                </ListItem>
                <ListItem
                  component="div"
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigateToSection('processes')}
                >
                  <ListItemIcon>
                    <AccountTreeIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Manage Processes"
                    secondary={
                      project.processCount
                        ? `${project.processCount} processes`
                        : 'No processes yet'
                    }
                  />
                </ListItem>
              </List>
            </Card>

            <Card sx={{ mt: 3 }}>
              <CardHeader title="Team Members" />
              <Divider />
              <List sx={{ maxHeight: 300, overflow: 'auto' }}>
                {project.members.length > 0 ? (
                  project.members.map((member) => (
                    <ListItem key={member.id}>
                      <ListItemIcon>
                        <PersonIcon />
                      </ListItemIcon>
                      <ListItemText
                        primary={member.user.full_name || member.user.email}
                        secondary={member.role.name}
                      />
                    </ListItem>
                  ))
                ) : (
                  <ListItem>
                    <ListItemText
                      primary="No team members yet"
                      secondary="Add members to collaborate on this project"
                    />
                  </ListItem>
                )}
              </List>
            </Card>
          </Grid>
        </Grid>
      )}
    </Container>
  );
};

export default ProjectDetails;
