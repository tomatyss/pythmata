/**
 * ImportExportButtons
 *
 * Component that provides UI buttons for importing and exporting BPMN diagrams.
 * Includes a file upload dialog for imports and handles the export process.
 */

import React, { useRef, useState } from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Snackbar,
  Alert,
  Box,
  Typography,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  FileUpload as FileUploadIcon,
  FileDownload as FileDownloadIcon,
  Close as CloseIcon,
} from '@mui/icons-material';

import { exportAsBpmn } from './BpmnExporter';
import { importBpmnFile, BpmnImportResult } from './BpmnImporter';

/**
 * Interface for the BPMN modeler instance
 */
interface BpmnModeler {
  importXML: (xml: string) => Promise<{ warnings: Array<string> }>;
  saveXML: (options?: { format?: boolean }) => Promise<{ xml: string }>;
}

/**
 * Props for the ImportExportButtons component
 */
interface ImportExportButtonsProps {
  modeler: BpmnModeler; // BPMN modeler instance
  processName: string;
  onImport?: (result: BpmnImportResult) => void;
  onBpmnXmlChange?: (xml: string) => void;
}

/**
 * Component that provides buttons for importing and exporting BPMN diagrams
 */
const ImportExportButtons: React.FC<ImportExportButtonsProps> = ({
  modeler,
  processName,
  onImport,
  onBpmnXmlChange,
}) => {
  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);

  // State
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  /**
   * Handles the export button click
   */
  const handleExport = async () => {
    try {
      await exportAsBpmn(modeler, processName);
      showNotification('BPMN diagram exported successfully', 'success');
    } catch (error) {
      console.error('Export error:', error);
      showNotification(
        `Failed to export BPMN diagram: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'error'
      );
    }
  };

  /**
   * Opens the file input dialog
   */
  const handleImportClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  /**
   * Opens the import dialog
   */
  const openImportDialog = () => {
    setImportDialogOpen(true);
  };

  /**
   * Closes the import dialog
   */
  const closeImportDialog = () => {
    setImportDialogOpen(false);
  };

  /**
   * Handles file selection from the file input
   */
  const handleFileSelect = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file) {
        await processImportFile(file);
        // Reset the file input
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    }
  };

  /**
   * Handles drag over events
   */
  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(true);
  };

  /**
   * Handles drag leave events
   */
  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
  };

  /**
   * Handles drop events
   */
  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);

    const files = event.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file) {
        await processImportFile(file);
      }
    }
  };

  /**
   * Processes an imported file
   */
  const processImportFile = async (file: File) => {
    try {
      const result = await importBpmnFile(file, modeler);

      if (result.success) {
        showNotification('BPMN diagram imported successfully', 'success');
        if (result.warnings && result.warnings.length > 0) {
          console.warn('Import warnings:', result.warnings);
        }

        // Update XML if callback provided
        if (result.xml && onBpmnXmlChange) {
          onBpmnXmlChange(result.xml);
        }

        // Call onImport callback if provided
        if (onImport) {
          onImport(result);
        }

        closeImportDialog();
      } else {
        showNotification(`Import failed: ${result.error}`, 'error');
      }
    } catch (error) {
      console.error('Import error:', error);
      showNotification(
        `Failed to import BPMN diagram: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'error'
      );
    }
  };

  /**
   * Shows a notification
   */
  const showNotification = (
    message: string,
    severity: 'success' | 'error' | 'info' | 'warning' = 'info'
  ) => {
    setNotification({
      open: true,
      message,
      severity,
    });
  };

  /**
   * Closes the notification
   */
  const closeNotification = () => {
    setNotification((prev) => ({ ...prev, open: false }));
  };

  return (
    <>
      {/* Export Button */}
      <Tooltip title="Export as BPMN">
        <Button
          variant="outlined"
          startIcon={<FileDownloadIcon />}
          onClick={handleExport}
          sx={{ mr: 1 }}
        >
          Export
        </Button>
      </Tooltip>

      {/* Import Button */}
      <Tooltip title="Import BPMN file">
        <Button
          variant="outlined"
          startIcon={<FileUploadIcon />}
          onClick={openImportDialog}
        >
          Import
        </Button>
      </Tooltip>

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        accept=".bpmn,.xml"
        onChange={handleFileSelect}
      />

      {/* Import Dialog */}
      <Dialog
        open={importDialogOpen}
        onClose={closeImportDialog}
        aria-labelledby="import-dialog-title"
      >
        <DialogTitle id="import-dialog-title">
          Import BPMN Diagram
          <IconButton
            aria-label="close"
            onClick={closeImportDialog}
            sx={{
              position: 'absolute',
              right: 8,
              top: 8,
            }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            Select a BPMN file (.bpmn or .xml) to import into the modeler.
          </DialogContentText>

          {/* Drag and Drop Area */}
          <Box
            sx={{
              mt: 2,
              p: 3,
              border: '2px dashed',
              borderColor: dragActive ? 'primary.main' : 'grey.400',
              borderRadius: 1,
              textAlign: 'center',
              bgcolor: dragActive ? 'action.hover' : 'background.paper',
              transition: 'all 0.2s ease',
            }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <FileUploadIcon
              sx={{
                fontSize: 48,
                color: dragActive ? 'primary.main' : 'text.secondary',
              }}
            />
            <Typography variant="body1" sx={{ mt: 1 }}>
              Drag and drop your BPMN file here
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              or
            </Typography>
            <Button
              variant="contained"
              onClick={handleImportClick}
              sx={{ mt: 1 }}
            >
              Select File
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeImportDialog} color="primary">
            Cancel
          </Button>
        </DialogActions>
      </Dialog>

      {/* Notification Snackbar */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={closeNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={closeNotification}
          severity={notification.severity}
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </>
  );
};

export default ImportExportButtons;
