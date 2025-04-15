/**
 * Project Descriptions Page
 * Displays and manages the descriptions of a project
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
  FormControl,
  IconButton,
  InputLabel,
  List,
  ListItem,
  ListItemIcon,
  ListItemSecondaryAction,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  TextField,
  Typography,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  Description as DescriptionIcon,
  ArrowBack as ArrowBackIcon,
  Visibility as VisibilityIcon,
  Check as CheckIcon,
  Label as LabelIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';

import { ROUTES } from '@/constants';
import PageHeader from '@/components/shared/PageHeader/PageHeader';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import ErrorMessage from '@/components/shared/ErrorMessage';
import useNotification from '@/hooks/useNotification';
import useConfirmDialog from '@/hooks/useConfirmDialog';
import projectService from '@/services/project';
import {
  Project,
  ProjectDescription,
  Tag,
  ProjectDescriptionCreate,
} from '@/types/project';

/**
 * Project Descriptions Page Component
 * Displays and manages the descriptions of a project
 */
const ProjectDescriptions = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showSuccess, showError } = useNotification();
  const { confirm } = useConfirmDialog();

  // State
  const [project, setProject] = useState<Project | null>(null);
  const [descriptions, setDescriptions] = useState<ProjectDescription[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [newDescriptionContent, setNewDescriptionContent] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

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
   * Fetch project descriptions from the API
   */
  const fetchDescriptions = useCallback(async () => {
    if (!id) return;

    try {
      const response = await projectService.getProjectDescriptions(id);
      setDescriptions(response.data);
    } catch (err) {
      console.error('Error fetching project descriptions:', err);
    }
  }, [id]);

  /**
   * Fetch tags from the API
   */
  const fetchTags = useCallback(async () => {
    try {
      const response = await projectService.getTags();
      setTags(response.data);
    } catch (err) {
      console.error('Error fetching tags:', err);
    }
  }, []);

  // Load project, descriptions, and tags on initial render
  useEffect(() => {
    fetchProject();
    fetchDescriptions();
    fetchTags();
  }, [id, fetchProject, fetchDescriptions, fetchTags]);

  /**
   * Handle adding a new description
   */
  const handleAddDescription = async () => {
    if (!id || !newDescriptionContent) return;

    try {
      setLoading(true);

      const descriptionData: ProjectDescriptionCreate = {
        content: newDescriptionContent,
        tagIds: selectedTags,
      };

      await projectService.createProjectDescription(id, descriptionData);
      showSuccess('Description added successfully');
      setAddDialogOpen(false);
      setNewDescriptionContent('');
      setSelectedTags([]);
      fetchProject();
      fetchDescriptions();
    } catch (err) {
      showError('Failed to add description');
      console.error('Error adding description:', err);
      setLoading(false);
    }
  };

  /**
   * Handle setting a description as current
   */
  const handleSetCurrentDescription = async (
    description: ProjectDescription
  ) => {
    if (!id) return;

    // If already current, do nothing
    if (description.isCurrent) return;

    const confirmed = await confirm({
      title: 'Set as Current Description',
      message: `Are you sure you want to set version ${description.version} as the current description?`,
      confirmText: 'Set as Current',
      confirmColor: 'primary',
    });

    if (confirmed) {
      try {
        setLoading(true);
        await projectService.setCurrentDescription(id, description.id);
        showSuccess('Current description updated successfully');
        fetchProject();
        fetchDescriptions();
      } catch (err) {
        showError('Failed to update current description');
        console.error('Error updating current description:', err);
        setLoading(false);
      }
    }
  };

  /**
   * Handle tag selection change
   */
  const handleTagChange = (event: SelectChangeEvent<string[]>) => {
    const { value } = event.target;
    setSelectedTags(typeof value === 'string' ? value.split(',') : value);
  };

  /**
   * Get tag color by ID
   */
  const getTagColor = (tagId: string): string => {
    const tag = tags.find((t) => t.id === tagId);
    return tag ? tag.color : '#808080';
  };

  /**
   * Get tag name by ID
   */
  const getTagName = (tagId: string): string => {
    const tag = tags.find((t) => t.id === tagId);
    return tag ? tag.name : 'Unknown';
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
        title="Project Descriptions"
        breadcrumbs={[
          { label: 'Projects', href: ROUTES.PROJECTS },
          { label: project.name, href: ROUTES.PROJECT_DETAILS(project.id) },
          { label: 'Descriptions' },
        ]}
        action={
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setAddDialogOpen(true)}
          >
            Add Description
          </Button>
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
          title="Project Descriptions"
          subheader={`${descriptions.length} versions`}
        />
        <Divider />
        <CardContent>
          {descriptions.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="textSecondary">
                No descriptions for this project yet.
              </Typography>
              <Typography
                variant="body2"
                color="textSecondary"
                sx={{ mt: 1, mb: 2 }}
              >
                Add a description to document project requirements and generate
                processes.
              </Typography>
              <Button
                variant="contained"
                color="primary"
                startIcon={<AddIcon />}
                onClick={() => setAddDialogOpen(true)}
              >
                Add Description
              </Button>
            </Box>
          ) : (
            <List>
              {descriptions.map((description) => (
                <ListItem
                  key={description.id}
                  divider
                  sx={{
                    bgcolor: description.isCurrent
                      ? 'rgba(0, 0, 0, 0.04)'
                      : 'transparent',
                  }}
                >
                  <ListItemIcon>
                    <DescriptionIcon
                      color={description.isCurrent ? 'primary' : 'action'}
                    />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Typography variant="subtitle1" component="span">
                          Version {description.version}
                        </Typography>
                        {description.isCurrent && (
                          <Chip
                            label="Current"
                            color="primary"
                            size="small"
                            sx={{ ml: 1 }}
                          />
                        )}
                      </Box>
                    }
                    secondary={
                      <>
                        <Typography
                          component="span"
                          variant="body2"
                          color="textSecondary"
                          sx={{
                            display: 'block',
                            maxHeight: '3em',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {description.content.substring(0, 100)}
                          {description.content.length > 100 ? '...' : ''}
                        </Typography>
                        <Typography
                          component="span"
                          variant="body2"
                          color="textSecondary"
                        >
                          Created on{' '}
                          {format(
                            new Date(description.createdAt),
                            'MMM d, yyyy'
                          )}
                        </Typography>
                        {description.tags.length > 0 && (
                          <Box sx={{ mt: 1 }}>
                            {description.tags.map((tag) => (
                              <Chip
                                key={tag.id}
                                label={tag.name}
                                size="small"
                                sx={{ mr: 1, bgcolor: tag.color }}
                              />
                            ))}
                          </Box>
                        )}
                      </>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Tooltip title="View Details">
                      <IconButton
                        edge="end"
                        aria-label="view"
                        onClick={() =>
                          navigate(
                            ROUTES.PROJECT_DESCRIPTION(
                              project.id,
                              description.id
                            )
                          )
                        }
                        sx={{ mr: 1 }}
                      >
                        <VisibilityIcon />
                      </IconButton>
                    </Tooltip>
                    {!description.isCurrent && (
                      <Tooltip title="Set as Current">
                        <IconButton
                          edge="end"
                          aria-label="set-current"
                          onClick={() =>
                            handleSetCurrentDescription(description)
                          }
                        >
                          <CheckIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </CardContent>
      </Card>

      {/* Add Description Dialog */}
      <Dialog
        open={addDialogOpen}
        onClose={() => setAddDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Add New Description</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              fullWidth
              label="Description Content"
              value={newDescriptionContent}
              onChange={(e) => setNewDescriptionContent(e.target.value)}
              margin="normal"
              variant="outlined"
              multiline
              rows={8}
              placeholder="Enter project requirements, specifications, or other details..."
            />
            <FormControl fullWidth margin="normal">
              <InputLabel id="tags-select-label">Tags</InputLabel>
              <Select
                labelId="tags-select-label"
                multiple
                value={selectedTags}
                onChange={handleTagChange}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((tagId) => (
                      <Chip
                        key={tagId}
                        label={getTagName(tagId)}
                        size="small"
                        sx={{ bgcolor: getTagColor(tagId) }}
                      />
                    ))}
                  </Box>
                )}
              >
                {tags.map((tag) => (
                  <MenuItem key={tag.id} value={tag.id}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <LabelIcon sx={{ mr: 1, color: tag.color }} />
                      {tag.name}
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleAddDescription}
            color="primary"
            variant="contained"
            disabled={!newDescriptionContent}
          >
            Add Description
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ProjectDescriptions;
