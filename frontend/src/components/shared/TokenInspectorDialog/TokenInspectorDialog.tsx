import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Box,
  Typography,
  Button,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';

interface TokenData {
  nodeId: string;
  state: string;
  scopeId?: string;
  data?: Record<string, unknown>;
}

interface TokenInspectorDialogProps {
  open: boolean;
  onClose: () => void;
  tokens: TokenData[];
  currentTokenIndex: number;
  onNavigateToken: (index: number) => void;
}

/**
 * A dialog component for inspecting token details in a process diagram
 * @param props Component properties including token data and navigation handlers
 * @returns TokenInspectorDialog component
 */
const TokenInspectorDialog = ({
  open,
  onClose,
  tokens,
  currentTokenIndex,
  onNavigateToken,
}: TokenInspectorDialogProps) => {
  const currentToken = tokens[currentTokenIndex];

  const handlePrevious = () => {
    onNavigateToken(currentTokenIndex - 1);
  };

  const handleNext = () => {
    onNavigateToken(currentTokenIndex + 1);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Token Inspector
        <IconButton
          aria-label="close"
          onClick={onClose}
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
        {currentToken && (
          <>
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" color="text.secondary">
                Token {currentTokenIndex + 1} of {tokens.length}
              </Typography>
            </Box>

            <Box sx={{ mb: 2 }}>
              <Typography variant="overline">State</Typography>
              <Typography variant="body1">{currentToken.state}</Typography>
            </Box>

            {currentToken.scopeId && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="overline">Scope ID</Typography>
                <Typography variant="body1">{currentToken.scopeId}</Typography>
              </Box>
            )}

            {currentToken.data && Object.keys(currentToken.data).length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="overline">Variables</Typography>
                <Box
                  sx={{
                    backgroundColor: '#f5f5f5',
                    p: 2,
                    borderRadius: 1,
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                  }}
                >
                  <pre style={{ margin: 0 }}>
                    {JSON.stringify(currentToken.data, null, 2)}
                  </pre>
                </Box>
              </Box>
            )}

            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                mt: 3,
              }}
            >
              <Button
                startIcon={<NavigateBeforeIcon />}
                onClick={handlePrevious}
                disabled={currentTokenIndex === 0}
              >
                Previous
              </Button>
              <Button
                endIcon={<NavigateNextIcon />}
                onClick={handleNext}
                disabled={currentTokenIndex === tokens.length - 1}
              >
                Next
              </Button>
            </Box>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default TokenInspectorDialog;
