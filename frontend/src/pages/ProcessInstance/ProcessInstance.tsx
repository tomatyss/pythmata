import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import apiService from '@/services/api';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Chip,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  Paper,
} from '@mui/material';

interface ProcessVariable {
  name: string;
  value: string | number | boolean | Record<string, unknown>;
  type: string;
  scope: string;
  updatedAt: string;
}

interface ActivityLog {
  id: string;
  type: string;
  nodeId: string;
  status: string;
  timestamp: string;
  details?: string;
}

interface ProcessInstanceDetails {
  id: string;
  definitionId: string;
  definitionName: string;
  status: string;
  startTime: string;
  endTime?: string;
  variables: ProcessVariable[];
  activities: ActivityLog[];
}

const ProcessInstance = () => {
  const { instanceId } = useParams();
  const [loading, setLoading] = useState(true);
  const [instance, setInstance] = useState<ProcessInstanceDetails | null>(null);

  useEffect(() => {
    const fetchInstanceData = async () => {
      if (!instanceId) return;

      try {
        setLoading(true);
        const response = await apiService.getProcessInstance(instanceId);
        const instanceData = response.data;

        setInstance({
          id: instanceData.id,
          definitionId: instanceData.definitionId,
          definitionName: instanceData.definitionName,
          status: instanceData.status,
          startTime: instanceData.startTime,
          endTime: instanceData.endTime,
          // For now, show empty arrays until API endpoints are available
          variables: [],
          activities: [],
        });
      } catch (error) {
        console.error('Failed to fetch instance:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchInstanceData();
  }, [instanceId]);

  if (loading || !instance) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Process Instance
      </Typography>

      <Grid container spacing={3}>
        {/* Instance Details */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Details
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography color="textSecondary">Instance ID</Typography>
                  <Typography>{instance.id}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography color="textSecondary">
                    Process Definition
                  </Typography>
                  <Typography>{instance.definitionName}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography color="textSecondary">Status</Typography>
                  <Chip
                    label={instance.status}
                    color={
                      instance.status === 'RUNNING'
                        ? 'primary'
                        : instance.status === 'COMPLETED'
                          ? 'success'
                          : 'error'
                    }
                    size="small"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography color="textSecondary">Start Time</Typography>
                  <Typography>
                    {new Date(instance.startTime).toLocaleString()}
                  </Typography>
                </Grid>
                {instance.endTime && (
                  <Grid item xs={12} sm={6}>
                    <Typography color="textSecondary">End Time</Typography>
                    <Typography>
                      {new Date(instance.endTime).toLocaleString()}
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Variables */}
        <Grid item xs={12} md={6}>
          <Paper>
            <Box sx={{ p: 2 }}>
              <Typography variant="h6">Variables</Typography>
            </Box>
            <Divider />
            <List>
              {instance.variables.map((variable) => (
                <ListItem key={variable.name}>
                  <ListItemText
                    primary={variable.name}
                    secondary={
                      <>
                        <Typography component="span" variant="body2">
                          Value: {JSON.stringify(variable.value)}
                        </Typography>
                        <br />
                        <Typography
                          component="span"
                          variant="body2"
                          color="textSecondary"
                        >
                          Type: {variable.type} | Scope: {variable.scope}
                        </Typography>
                      </>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>

        {/* Activity Log */}
        <Grid item xs={12} md={6}>
          <Paper>
            <Box sx={{ p: 2 }}>
              <Typography variant="h6">Activity Log</Typography>
            </Box>
            <Divider />
            <List>
              {instance.activities.map((activity) => (
                <ListItem key={activity.id}>
                  <ListItemText
                    primary={
                      <Box
                        sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                      >
                        <Typography>{activity.type}</Typography>
                        <Chip
                          label={activity.status}
                          size="small"
                          color={
                            activity.status === 'completed'
                              ? 'success'
                              : activity.status === 'running'
                                ? 'primary'
                                : 'default'
                          }
                        />
                      </Box>
                    }
                    secondary={
                      <>
                        <Typography component="span" variant="body2">
                          Node: {activity.nodeId}
                        </Typography>
                        <br />
                        {activity.details && (
                          <>
                            <Typography component="span" variant="body2">
                              {activity.details}
                            </Typography>
                            <br />
                          </>
                        )}
                        <Typography
                          component="span"
                          variant="body2"
                          color="textSecondary"
                        >
                          {new Date(activity.timestamp).toLocaleString()}
                        </Typography>
                      </>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ProcessInstance;
