import React, { useState } from 'react';
import { Box, Button, Typography, Tooltip } from '@mui/material';
import HistoryIcon from '@mui/icons-material/History';
import VersionHistory from './VersionHistory';
import { Version } from '@/types/version';

interface VersionSelectorProps {
  processId: string;
  version?: string | number;
  onVersionChange?: (version: Version) => void;
}

const VersionSelector: React.FC<VersionSelectorProps> = ({
  processId,
  version,
  onVersionChange,
}) => {
  const [historyOpen, setHistoryOpen] = useState(false);

  const handleOpenHistory = () => {
    setHistoryOpen(true);
  };

  const handleCloseHistory = () => {
    setHistoryOpen(false);
  };

  const handleVersionSelect = (selectedVersion: Version) => {
    if (onVersionChange) {
      onVersionChange(selectedVersion);
    }
  };

  return (
    <>
      <Box display="flex" alignItems="center" gap={1}>
        {version && (
          <Tooltip title="Current version">
            <Typography variant="subtitle1" component="span">
              v{version}
            </Typography>
          </Tooltip>
        )}
        <Tooltip title="View version history">
          <Button
            size="small"
            startIcon={<HistoryIcon />}
            onClick={handleOpenHistory}
            variant="outlined"
          >
            History
          </Button>
        </Tooltip>
      </Box>

      <VersionHistory
        open={historyOpen}
        onClose={handleCloseHistory}
        processId={processId}
        currentVersion={version?.toString()}
        onVersionSelect={handleVersionSelect}
      />
    </>
  );
};

export default VersionSelector;
