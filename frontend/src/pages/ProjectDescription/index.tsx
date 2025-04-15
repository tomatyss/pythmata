/**
 * Project Description Page
 * Displays a single project description in detail
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
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
  Paper,
  Typography,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Check as CheckIcon,
  Description as DescriptionIcon,
  AccountTree as AccountTreeIcon,
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
  ProjectDescription as ProjectDescriptionType,
} from '@/types/project';

/**
 * Project Description Page Component
 * Displays a single project description in detail
 */
const ProjectDescription = () => {
  const { id, descriptionId } = useParams<{
    id: string;
    descriptionId: string;
  }>();
  const { showSuccess, showError } = useNotification();
  const { confirm } = useConfirmDialog();

  // State
  const [project, setProject] = useState<Project | null>(null);
  const [description, setDescription] = useState<ProjectDescriptionType | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
   * Fetch description details from the API
   */
  const fetchDescription = useCallback(async () => {
    if (!id || !descriptionId) return;

    try {
      setLoading(true);
      setError(null);

      const response = await projectService.getProjectDescription(
        id,
        descriptionId
      );
      setDescription(response.data);
      setLoading(false);
    } catch (err) {
      setLoading(false);
      setError('Failed to load description details. Please try again.');
      console.error('Error fetching description:', err);
    }
  }, [id, descriptionId]);

  // Load project and description on initial render
  useEffect(() => {
    fetchProject();
    fetchDescription();
  }, [id, descriptionId, fetchProject, fetchDescription]);

  /**
   * Handle setting description as current
   */
  const handleSetAsCurrent = async () => {
    if (!id || !descriptionId || !description) return;

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
        await projectService.setCurrentDescription(id, descriptionId);
        showSuccess('Current description updated successfully');
        fetchDescription();
      } catch (err) {
        showError('Failed to update current description');
        console.error('Error updating current description:', err);
        setLoading(false);
      }
    }
  };

  /**
   * Handle generating process from description
   */
  const handleGenerateProcess = () => {
    // This would navigate to a process creation page with the description pre-loaded
    // For now, we'll just show a message
    showSuccess('Process generation would be implemented here');
  };

  if (loading && (!project || !description)) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage message={error} />;
  }

  if (!project || !description) {
    return <ErrorMessage message="Project or description not found" />;
  }

  return (
    <Container maxWidth="lg">
      <PageHeader
        title={`Description - Version ${description.version}`}
        breadcrumbs={[
          { label: 'Projects', href: ROUTES.PROJECTS },
          { label: project.name, href: ROUTES.PROJECT_DETAILS(project.id) },
          {
            label: 'Descriptions',
            href: ROUTES.PROJECT_DESCRIPTIONS(project.id),
          },
          { label: `Version ${description.version}` },
        ]}
        action={
          !description.isCurrent ? (
            <Button
              variant="contained"
              color="primary"
              startIcon={<CheckIcon />}
              onClick={handleSetAsCurrent}
            >
              Set as Current
            </Button>
          ) : (
            <Button
              variant="contained"
              color="primary"
              startIcon={<AccountTreeIcon />}
              onClick={handleGenerateProcess}
            >
              Generate Process
            </Button>
          )
        }
      />

      <Paper sx={{ p: 2, mb: 3 }}>
        <Button
          component={RouterLink}
          to={ROUTES.PROJECT_DESCRIPTIONS(project.id)}
          startIcon={<ArrowBackIcon />}
        >
          Back to Descriptions
        </Button>
      </Paper>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardHeader
              title={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <DescriptionIcon sx={{ mr: 1 }} />
                  <Typography variant="h6">Description Content</Typography>
                  {description.isCurrent && (
                    <Chip
                      label="Current"
                      color="primary"
                      size="small"
                      sx={{ ml: 2 }}
                    />
                  )}
                </Box>
              }
              subheader={`Version ${description.version} - Created on ${format(new Date(description.createdAt), 'MMMM d, yyyy')}`}
            />
            <Divider />
            <CardContent>
              <Typography
                variant="body1"
                component="div"
                sx={{ whiteSpace: 'pre-wrap' }}
              >
                {description.content}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardHeader title="Information" />
            <Divider />
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                Version
              </Typography>
              <Typography variant="body2" paragraph>
                {description.version}
              </Typography>

              <Typography variant="subtitle2" gutterBottom>
                Status
              </Typography>
              <Typography variant="body2" paragraph>
                {description.isCurrent ? (
                  <Chip label="Current Version" color="primary" size="small" />
                ) : (
                  <Chip label="Previous Version" color="default" size="small" />
                )}
              </Typography>

              <Typography variant="subtitle2" gutterBottom>
                Created
              </Typography>
              <Typography variant="body2" paragraph>
                {format(new Date(description.createdAt), 'MMMM d, yyyy')}
              </Typography>

              <Typography variant="subtitle2" gutterBottom>
                Tags
              </Typography>
              <Box sx={{ mt: 1 }}>
                {description.tags.length > 0 ? (
                  description.tags.map((tag) => (
                    <Chip
                      key={tag.id}
                      label={tag.name}
                      size="small"
                      sx={{ mr: 1, mb: 1, bgcolor: tag.color }}
                    />
                  ))
                ) : (
                  <Typography variant="body2">No tags</Typography>
                )}
              </Box>
            </CardContent>
          </Card>

          <Card sx={{ mt: 3 }}>
            <CardHeader title="Actions" />
            <Divider />
            <CardContent>
              <Button
                fullWidth
                variant="contained"
                color="primary"
                startIcon={<AccountTreeIcon />}
                onClick={handleGenerateProcess}
                sx={{ mb: 2 }}
              >
                Generate Process
              </Button>

              {!description.isCurrent && (
                <Button
                  fullWidth
                  variant="outlined"
                  color="primary"
                  startIcon={<CheckIcon />}
                  onClick={handleSetAsCurrent}
                >
                  Set as Current Version
                </Button>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default ProjectDescription;
