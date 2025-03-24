import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

interface VersionCompareProps {
  sourceVersionId: string;
  targetVersionId: string;
}

/**
 * VersionCompare component to visualize differences between two versions
 * This is a placeholder for future implementation
 */
const VersionCompare: React.FC<VersionCompareProps> = ({
  sourceVersionId,
  targetVersionId,
}) => {
  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Version Comparison
      </Typography>
      <Box sx={{ my: 2 }}>
        <Typography variant="body1">
          Comparing versions {sourceVersionId} and {targetVersionId}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Detailed version comparison functionality will be implemented in a
          future update.
        </Typography>
      </Box>
    </Paper>
  );
};

export default VersionCompare;
