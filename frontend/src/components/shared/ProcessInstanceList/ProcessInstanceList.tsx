import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Typography,
  Paper,
} from '@mui/material';

interface ProcessInstance {
  id: string;
  startDate: string;
  endDate?: string;
  state: string;
}

interface ProcessInstanceListProps {
  instances: ProcessInstance[];
  selectedInstanceId?: string;
  onSelectInstance: (instanceId: string) => void;
}

/**
 * A component that displays a list of process instances with their details
 * @param props Component properties including instance data and selection handler
 * @returns ProcessInstanceList component
 */
const ProcessInstanceList = ({
  instances,
  selectedInstanceId,
  onSelectInstance,
}: ProcessInstanceListProps) => {
  return (
    <Paper
      elevation={0}
      variant="outlined"
      sx={{
        height: '100%',
        minWidth: 300,
        maxWidth: 400,
        overflow: 'auto',
      }}
    >
      <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0' }}>
        <Typography variant="h6" component="h2">
          Process Instances ({instances.length})
        </Typography>
      </Box>

      <List sx={{ p: 0 }}>
        {instances.map((instance) => (
          <ListItem key={instance.id} disablePadding divider>
            <ListItemButton
              selected={instance.id === selectedInstanceId}
              onClick={() => onSelectInstance(instance.id)}
              sx={{
                '&.Mui-selected': {
                  backgroundColor: '#e3f2fd',
                  '&:hover': {
                    backgroundColor: '#e3f2fd',
                  },
                },
              }}
            >
              <ListItemText
                primary={instance.id}
                secondary={
                  <Box component="span" sx={{ display: 'block' }}>
                    <Typography
                      component="span"
                      variant="body2"
                      color="text.primary"
                      sx={{ display: 'block' }}
                    >
                      Started: {new Date(instance.startDate).toLocaleString()}
                    </Typography>
                    {instance.endDate && (
                      <Typography
                        component="span"
                        variant="body2"
                        color="text.primary"
                        sx={{ display: 'block' }}
                      >
                        Ended: {new Date(instance.endDate).toLocaleString()}
                      </Typography>
                    )}
                    <Typography
                      component="span"
                      variant="body2"
                      sx={{
                        display: 'inline-block',
                        color:
                          instance.state === 'active'
                            ? 'success.main'
                            : 'text.secondary',
                        mt: 0.5,
                      }}
                    >
                      {instance.state}
                    </Typography>
                  </Box>
                }
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};

export default ProcessInstanceList;
