/**
 * Project Members Page
 * Displays and manages the members of a project
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
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
  ListItemAvatar,
  ListItemSecondaryAction,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  TextField,
  Typography,
  Avatar,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Person as PersonIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';

import { ROUTES } from '@/constants';
import PageHeader from '@/components/shared/PageHeader/PageHeader';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import ErrorMessage from '@/components/shared/ErrorMessage';
import useNotification from '@/hooks/useNotification';
import useConfirmDialog from '@/hooks/useConfirmDialog';
import projectService from '@/services/project';
import {
  Project,
  ProjectMember,
  ProjectRole,
  ProjectMemberCreate,
  ProjectMemberUpdate,
} from '@/types/project';

/**
 * Project Members Page Component
 * Displays and manages the members of a project
 */
const ProjectMembers = () => {
  const { id } = useParams<{ id: string }>();
  const { showSuccess, showError } = useNotification();
  const { confirm } = useConfirmDialog();

  // State
  const [project, setProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [roles, setRoles] = useState<ProjectRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<ProjectMember | null>(
    null
  );
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRoleId, setNewMemberRoleId] = useState('');
  const [editMemberRoleId, setEditMemberRoleId] = useState('');

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
      setMembers(response.data.members);
      setLoading(false);
    } catch (err) {
      setLoading(false);
      setError('Failed to load project details. Please try again.');
      console.error('Error fetching project:', err);
    }
  }, [id]);

  /**
   * Fetch project roles from the API
   */
  const fetchRoles = useCallback(async () => {
    if (!id) return;

    try {
      const response = await projectService.getProjectRoles(id);
      setRoles(response.data);
    } catch (err) {
      console.error('Error fetching project roles:', err);
    }
  }, [id]);

  // Load project and roles on initial render
  useEffect(() => {
    fetchProject();
    fetchRoles();
  }, [id, fetchProject, fetchRoles]);

  /**
   * Handle adding a new member
   */
  const handleAddMember = async () => {
    if (!id || !newMemberEmail || !newMemberRoleId) return;

    try {
      setLoading(true);

      // In a real app, you would search for the user by email first
      // For now, we'll assume the email corresponds to a user ID
      const memberData: ProjectMemberCreate = {
        userId: newMemberEmail, // This would normally be a user ID
        roleId: newMemberRoleId,
      };

      await projectService.addProjectMember(id, memberData);
      showSuccess('Member added successfully');
      setAddDialogOpen(false);
      setNewMemberEmail('');
      setNewMemberRoleId('');
      fetchProject();
    } catch (err) {
      showError('Failed to add member');
      console.error('Error adding member:', err);
      setLoading(false);
    }
  };

  /**
   * Handle updating a member's role
   */
  const handleUpdateMember = async () => {
    if (!id || !selectedMember || !editMemberRoleId) return;

    try {
      setLoading(true);

      const memberData: ProjectMemberUpdate = {
        roleId: editMemberRoleId,
      };

      await projectService.updateProjectMember(
        id,
        selectedMember.user.id,
        memberData
      );
      showSuccess('Member updated successfully');
      setEditDialogOpen(false);
      setSelectedMember(null);
      setEditMemberRoleId('');
      fetchProject();
    } catch (err) {
      showError('Failed to update member');
      console.error('Error updating member:', err);
      setLoading(false);
    }
  };

  /**
   * Handle removing a member
   */
  const handleRemoveMember = async (member: ProjectMember) => {
    if (!id) return;

    const confirmed = await confirm({
      title: 'Remove Member',
      message: `Are you sure you want to remove ${member.user.full_name || member.user.email} from this project?`,
      confirmText: 'Remove',
      confirmColor: 'error',
    });

    if (confirmed) {
      try {
        setLoading(true);
        await projectService.removeProjectMember(id, member.user.id);
        showSuccess('Member removed successfully');
        fetchProject();
      } catch (err) {
        showError('Failed to remove member');
        console.error('Error removing member:', err);
        setLoading(false);
      }
    }
  };

  /**
   * Open edit dialog for a member
   */
  const openEditDialog = (member: ProjectMember) => {
    setSelectedMember(member);
    setEditMemberRoleId(member.role.id);
    setEditDialogOpen(true);
  };

  /**
   * Handle role selection change
   */
  const handleRoleChange = (event: SelectChangeEvent) => {
    setNewMemberRoleId(event.target.value);
  };

  /**
   * Handle edit role selection change
   */
  const handleEditRoleChange = (event: SelectChangeEvent) => {
    setEditMemberRoleId(event.target.value);
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
        title="Project Members"
        breadcrumbs={[
          { label: 'Projects', href: ROUTES.PROJECTS },
          { label: project.name, href: ROUTES.PROJECT_DETAILS(project.id) },
          { label: 'Members' },
        ]}
        action={
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setAddDialogOpen(true)}
          >
            Add Member
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
          title="Team Members"
          subheader={`${members.length} members in this project`}
        />
        <Divider />
        <CardContent>
          {members.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="textSecondary">
                No members in this project yet.
              </Typography>
              <Button
                variant="contained"
                color="primary"
                startIcon={<AddIcon />}
                onClick={() => setAddDialogOpen(true)}
                sx={{ mt: 2 }}
              >
                Add Member
              </Button>
            </Box>
          ) : (
            <List>
              {members.map((member) => (
                <ListItem key={member.id} divider>
                  <ListItemAvatar>
                    <Avatar>
                      <PersonIcon />
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={member.user.full_name || member.user.email}
                    secondary={
                      <>
                        <Typography
                          component="span"
                          variant="body2"
                          color="textPrimary"
                        >
                          {member.role.name}
                        </Typography>
                        {' — '}
                        <Typography
                          component="span"
                          variant="body2"
                          color="textSecondary"
                        >
                          Joined on{' '}
                          {new Date(member.joinedAt).toLocaleDateString()}
                        </Typography>
                      </>
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      aria-label="edit"
                      onClick={() => openEditDialog(member)}
                      sx={{ mr: 1 }}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      edge="end"
                      aria-label="delete"
                      onClick={() => handleRemoveMember(member)}
                      disabled={member.user.id === project.owner.id} // Can't remove the owner
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </CardContent>
      </Card>

      {/* Add Member Dialog */}
      <Dialog
        open={addDialogOpen}
        onClose={() => setAddDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Team Member</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              fullWidth
              label="Email Address"
              value={newMemberEmail}
              onChange={(e) => setNewMemberEmail(e.target.value)}
              margin="normal"
              variant="outlined"
              helperText="Enter the email address of the user you want to add"
            />
            <FormControl fullWidth margin="normal">
              <InputLabel id="role-select-label">Role</InputLabel>
              <Select
                labelId="role-select-label"
                value={newMemberRoleId}
                onChange={handleRoleChange}
                label="Role"
              >
                {roles.map((role) => (
                  <MenuItem key={role.id} value={role.id}>
                    {role.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleAddMember}
            color="primary"
            variant="contained"
            disabled={!newMemberEmail || !newMemberRoleId}
          >
            Add Member
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Member Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Team Member</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <Typography variant="subtitle1" gutterBottom>
              {selectedMember?.user.full_name || selectedMember?.user.email}
            </Typography>
            <FormControl fullWidth margin="normal">
              <InputLabel id="edit-role-select-label">Role</InputLabel>
              <Select
                labelId="edit-role-select-label"
                value={editMemberRoleId}
                onChange={handleEditRoleChange}
                label="Role"
              >
                {roles.map((role) => (
                  <MenuItem key={role.id} value={role.id}>
                    {role.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleUpdateMember}
            color="primary"
            variant="contained"
            disabled={!editMemberRoleId}
          >
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ProjectMembers;
