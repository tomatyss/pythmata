/**
 * Project Create Page
 * Form for creating a new project
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Container,
  FormControl,
  FormHelperText,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material';
import { useFormik } from 'formik';
import * as Yup from 'yup';

import { ROUTES, PROJECT_STATUS, VALIDATION } from '@/constants';
import PageHeader from '@/components/shared/PageHeader/PageHeader';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import useNotification from '@/hooks/useNotification';
import projectService from '@/services/project';
import { ProjectCreate as ProjectCreateType } from '@/types/project';

/**
 * Validation schema for project creation form
 */
const validationSchema = Yup.object({
  name: Yup.string()
    .required('Name is required')
    .min(
      VALIDATION.NAME_MIN_LENGTH,
      `Name must be at least ${VALIDATION.NAME_MIN_LENGTH} characters`
    )
    .max(
      VALIDATION.NAME_MAX_LENGTH,
      `Name cannot exceed ${VALIDATION.NAME_MAX_LENGTH} characters`
    ),
  description: Yup.string().max(
    VALIDATION.DESCRIPTION_MAX_LENGTH,
    `Description cannot exceed ${VALIDATION.DESCRIPTION_MAX_LENGTH} characters`
  ),
  status: Yup.string().required('Status is required'),
});

/**
 * Project Create Page Component
 * Form for creating a new project
 */
const ProjectCreate = () => {
  const navigate = useNavigate();
  const { showSuccess, showError } = useNotification();
  const [loading, setLoading] = useState(false);

  /**
   * Handle form submission
   * @param values - Form values
   */
  const handleSubmit = async (values: ProjectCreateType) => {
    try {
      setLoading(true);
      const response = await projectService.createProject(values);
      showSuccess('Project created successfully');
      navigate(ROUTES.PROJECT_DETAILS(response.data.id));
    } catch (err) {
      showError('Failed to create project');
      console.error('Error creating project:', err);
      setLoading(false);
    }
  };

  /**
   * Form handling with Formik
   */
  const formik = useFormik({
    initialValues: {
      name: '',
      description: '',
      status: PROJECT_STATUS.DRAFT,
    },
    validationSchema,
    onSubmit: handleSubmit,
  });

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <Container maxWidth="md">
      <PageHeader
        title="Create New Project"
        breadcrumbs={[
          { label: 'Projects', href: ROUTES.PROJECTS },
          { label: 'Create New Project' },
        ]}
      />

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <form onSubmit={formik.handleSubmit}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  id="name"
                  name="name"
                  label="Project Name"
                  value={formik.values.name}
                  onChange={formik.handleChange}
                  onBlur={formik.handleBlur}
                  error={formik.touched.name && Boolean(formik.errors.name)}
                  helperText={formik.touched.name && formik.errors.name}
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
                  value={formik.values.description}
                  onChange={formik.handleChange}
                  onBlur={formik.handleBlur}
                  error={
                    formik.touched.description &&
                    Boolean(formik.errors.description)
                  }
                  helperText={
                    formik.touched.description && formik.errors.description
                  }
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl
                  fullWidth
                  error={formik.touched.status && Boolean(formik.errors.status)}
                >
                  <InputLabel id="status-label">Status</InputLabel>
                  <Select
                    labelId="status-label"
                    id="status"
                    name="status"
                    value={formik.values.status}
                    onChange={formik.handleChange}
                    onBlur={formik.handleBlur}
                    label="Status"
                  >
                    {Object.values(PROJECT_STATUS).map((status) => (
                      <MenuItem key={status} value={status}>
                        {status}
                      </MenuItem>
                    ))}
                  </Select>
                  {formik.touched.status && formik.errors.status && (
                    <FormHelperText>{formik.errors.status}</FormHelperText>
                  )}
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
                    onClick={() => navigate(ROUTES.PROJECTS)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="contained"
                    color="primary"
                    disabled={formik.isSubmitting || !formik.isValid}
                  >
                    Create Project
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </form>
        </CardContent>
      </Card>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            What happens next?
          </Typography>
          <Typography variant="body2" paragraph>
            After creating a project, you can:
          </Typography>
          <ul>
            <Typography component="li" variant="body2">
              Add team members to collaborate on the project
            </Typography>
            <Typography component="li" variant="body2">
              Create project descriptions to document requirements
            </Typography>
            <Typography component="li" variant="body2">
              Create and attach process definitions to implement the project
            </Typography>
            <Typography component="li" variant="body2">
              Use the chat interface to generate processes from descriptions
            </Typography>
          </ul>
        </CardContent>
      </Card>
    </Container>
  );
};

export default ProjectCreate;
