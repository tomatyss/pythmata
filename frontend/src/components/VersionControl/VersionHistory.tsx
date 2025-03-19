import React, { useEffect, useState, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Divider,
  Typography,
  Box,
  CircularProgress,
  Chip,
} from '@mui/material';
import { formatDistanceToNow } from 'date-fns';
import apiService from '@/services/api';
import { BranchType, Version } from '@/types/version';

interface VersionHistoryProps {
  open: boolean;
  onClose: () => void;
  processId: string;
  currentVersion?: string;
  onVersionSelect?: (version: Version) => void;
}

const getBranchTypeColor = (branchType: BranchType) => {
  switch (branchType) {
    case BranchType.MAIN:
      return 'primary';
    case BranchType.FEATURE:
      return 'success';
    case BranchType.BUGFIX:
      return 'warning';
    case BranchType.RELEASE:
      return 'info';
    default:
      return 'default';
  }
};

const VersionHistory: React.FC<VersionHistoryProps> = ({
  open,
  onClose,
  processId,
  currentVersion,
  onVersionSelect,
}) => {
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadVersions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getProcessVersions(processId);
      setVersions(response.data.versions);
    } catch (err) {
      setError('Failed to load version history');
      console.error('Error loading versions:', err);
    } finally {
      setLoading(false);
    }
  }, [processId]);

  useEffect(() => {
    if (open && processId) {
      loadVersions();
    }
  }, [open, processId, loadVersions]);

  const handleVersionSelect = (version: Version) => {
    if (onVersionSelect) {
      onVersionSelect(version);
    }
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Version History</DialogTitle>
      <DialogContent dividers>
        {loading ? (
          <Box display="flex" justifyContent="center" my={4}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error" align="center">
            {error}
          </Typography>
        ) : versions.length === 0 ? (
          <Typography align="center">No version history available.</Typography>
        ) : (
          <List>
            {versions.map((version, index) => (
              <React.Fragment key={version.id}>
                {index > 0 && <Divider />}
                <ListItem disablePadding>
                  <ListItemButton
                    onClick={() => handleVersionSelect(version)}
                    selected={version.versionNumber === currentVersion}
                  >
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography
                            variant="subtitle1"
                            component="span"
                            fontWeight={
                              version.versionNumber === currentVersion
                                ? 'bold'
                                : 'normal'
                            }
                          >
                            v{version.versionNumber}
                          </Typography>
                          <Chip
                            label={version.branchType}
                            size="small"
                            color={getBranchTypeColor(version.branchType)}
                          />
                          {version.branchName && (
                            <Typography
                              variant="body2"
                              component="span"
                              color="textSecondary"
                            >
                              ({version.branchName})
                            </Typography>
                          )}
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" component="span">
                            {version.commitMessage}
                          </Typography>
                          <Box
                            display="flex"
                            justifyContent="space-between"
                            mt={0.5}
                            color="text.secondary"
                          >
                            <Typography variant="caption">
                              By {version.author}
                            </Typography>
                            <Typography variant="caption">
                              {formatDistanceToNow(
                                new Date(version.createdAt),
                                {
                                  addSuffix: true,
                                }
                              )}
                            </Typography>
                          </Box>
                        </Box>
                      }
                    />
                  </ListItemButton>
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="primary">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default VersionHistory;
