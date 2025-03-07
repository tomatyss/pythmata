import { useEffect, useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import apiService from '@/services/api';
import { formatDate } from '@/utils/dateUtils';
import ProcessDiagramViewer from '@/components/shared/ProcessDiagramViewer';
import { useProcessTokens } from '@/hooks/useProcessTokens';
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
import {
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Pause as PauseIcon,
  PlayCircle as ResumeIcon,
  Error as ErrorIcon,
  CheckCircle as CompletedIcon,
  ArrowForward as NodeIcon,
  Add as CreateIcon,
  Settings as ServiceIcon,
} from '@mui/icons-material';

interface ProcessVariable {
  name: string;
  value: string | number | boolean | Record<string, unknown>;
  type: string;
  scope: string;
  updatedAt: string;
}

import { ActivityLog, ActivityType } from '@/types/process';

interface ProcessInstanceDetails {
  id: string;
  definitionId: string;
  definitionName: string;
  status: string;
  startTime: string;
  endTime?: string;
  variables: ProcessVariable[];
  activities: ActivityLog[];
  bpmnXml?: string;
}

const ProcessInstance = () => {
  const { instanceId } = useParams();
  const [loading, setLoading] = useState(true);
  const [instance, setInstance] = useState<ProcessInstanceDetails | null>(null);

  // Memoize the enabled state to prevent unnecessary hook re-runs
  const isPollingEnabled = useMemo(
    () => !!instanceId && instance?.status === 'RUNNING',
    [instanceId, instance?.status]
  );

  const { tokens } = useProcessTokens({
    instanceId: instanceId || '',
    enabled: isPollingEnabled,
    pollingInterval: 2000,
  });

  useEffect(() => {
    const fetchInstanceData = async () => {
      if (!instanceId) return;

      try {
        setLoading(true);
        // Get instance data, definition, and activities
        const [instanceResponse, activitiesResponse] = await Promise.all([
          apiService.getProcessInstance(instanceId),
          apiService.getInstanceActivities(instanceId),
        ]);
        const instanceData = instanceResponse.data;

        // Get process definition
        const definitionResponse = await apiService.getProcessDefinition(
          instanceData.definitionId
        );
        const definitionData = definitionResponse.data;

        setInstance({
          id: instanceData.id,
          definitionId: instanceData.definitionId,
          definitionName: instanceData.definitionName,
          status: instanceData.status,
          startTime: instanceData.startTime,
          endTime: instanceData.endTime,
          variables: [],
          activities: activitiesResponse.data,
          bpmnXml: definitionData.bpmnXml,
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
        {/* Process Diagram */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Process Diagram
              </Typography>
              <Box sx={{ height: '500px' }}>
                {instance.bpmnXml && (
                  <ProcessDiagramViewer
                    bpmnXml={instance.bpmnXml}
                    tokens={tokens}
                  />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
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
                  <Typography>{formatDate(instance.startTime)}</Typography>
                </Grid>
                {instance.endTime && (
                  <Grid item xs={12} sm={6}>
                    <Typography color="textSecondary">End Time</Typography>
                    <Typography>{formatDate(instance.endTime)}</Typography>
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
                        {activity.activityType ===
                          ActivityType.INSTANCE_CREATED && (
                          <CreateIcon color="primary" />
                        )}
                        {activity.activityType ===
                          ActivityType.INSTANCE_STARTED && (
                          <StartIcon color="primary" />
                        )}
                        {activity.activityType ===
                          ActivityType.NODE_ENTERED && (
                          <NodeIcon color="primary" />
                        )}
                        {activity.activityType ===
                          ActivityType.NODE_COMPLETED && (
                          <CompletedIcon color="success" />
                        )}
                        {activity.activityType ===
                          ActivityType.INSTANCE_SUSPENDED && (
                          <PauseIcon color="warning" />
                        )}
                        {activity.activityType ===
                          ActivityType.INSTANCE_RESUMED && (
                          <ResumeIcon color="primary" />
                        )}
                        {activity.activityType ===
                          ActivityType.INSTANCE_COMPLETED && (
                          <StopIcon color="success" />
                        )}
                        {activity.activityType ===
                          ActivityType.INSTANCE_ERROR && (
                          <ErrorIcon color="error" />
                        )}
                        {activity.activityType ===
                          ActivityType.SERVICE_TASK_EXECUTED && (
                          <ServiceIcon
                            color={
                              activity.details?.status === 'ERROR'
                                ? 'error'
                                : 'success'
                            }
                          />
                        )}
                        <Typography>
                          {activity.activityType
                            .split('_')
                            .map(
                              (word) =>
                                word.charAt(0) + word.slice(1).toLowerCase()
                            )
                            .join(' ')}
                        </Typography>
                      </Box>
                    }
                    secondary={
                      <>
                        {activity.nodeId && (
                          <>
                            <Typography component="span" variant="body2">
                              Node: {activity.nodeId}
                            </Typography>
                            <br />
                          </>
                        )}

                        {/* Service Task Executed details */}
                        {activity.activityType ===
                          ActivityType.SERVICE_TASK_EXECUTED &&
                          activity.details && (
                            <>
                              <Typography component="span" variant="body2">
                                Service: {String(activity.details.service_task)}
                              </Typography>
                              <br />
                              {activity.details.status === 'ERROR' ? (
                                <Typography
                                  component="span"
                                  variant="body2"
                                  color="error"
                                >
                                  Error: {String(activity.details.error)}
                                </Typography>
                              ) : (
                                <Typography component="span" variant="body2">
                                  Result:{' '}
                                  {JSON.stringify(
                                    activity.details.result || {}
                                  )}
                                </Typography>
                              )}
                              <br />
                            </>
                          )}

                        {/* Other activity details */}
                        {activity.activityType !==
                          ActivityType.SERVICE_TASK_EXECUTED &&
                          activity.details && (
                            <>
                              <Typography component="span" variant="body2">
                                Details: {JSON.stringify(activity.details)}
                              </Typography>
                              <br />
                            </>
                          )}

                        <Typography
                          component="span"
                          variant="body2"
                          color="textSecondary"
                        >
                          {formatDate(activity.timestamp)} (
                          {formatDate(activity.createdAt)})
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
