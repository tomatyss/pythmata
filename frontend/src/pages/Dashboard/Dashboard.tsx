import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Button,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayArrowIcon,
  Error as ErrorIcon,
  CheckCircle as CheckCircleIcon,
  AccessTime as AccessTimeIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import { ProcessStats, ProcessStatus } from '@/types/process';
import apiService from '@/services/api';

const Dashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<ProcessStats>({
    totalInstances: 0,
    statusCounts: {
      [ProcessStatus.RUNNING]: 0,
      [ProcessStatus.COMPLETED]: 0,
      [ProcessStatus.SUSPENDED]: 0,
      [ProcessStatus.ERROR]: 0,
    },
    averageCompletionTime: null,
    errorRate: 0,
    activeInstances: 0,
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiService.getProcessStats();
        setStats(response.data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
        setError('Failed to load process statistics');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  const formatDuration = (seconds: number | null): string => {
    if (seconds === null) return 'N/A';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  const StatCard = ({
    title,
    value,
    icon: Icon,
    color,
    tooltip,
  }: {
    title: string;
    value: string | number;
    icon: React.ElementType;
    color: string;
    tooltip?: string;
  }) => (
    <Tooltip title={tooltip || ''} arrow>
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Icon sx={{ color, mr: 1 }} />
            <Typography color="textSecondary" variant="h6">
              {title}
            </Typography>
          </Box>
          <Typography variant="h4">{value}</Typography>
        </CardContent>
      </Card>
    </Tooltip>
  );

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error">{error}</Typography>
        <Button
          variant="contained"
          onClick={() => window.location.reload()}
          sx={{ mt: 2 }}
        >
          Retry
        </Button>
      </Box>
    );
  }

  if (loading) {
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
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 4,
        }}
      >
        <Typography variant="h4">Dashboard</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/processes/new')}
        >
          New Process
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Processes"
            value={stats.totalInstances}
            icon={AddIcon}
            color="#1976d2"
            tooltip="Total number of process instances"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Active"
            value={stats.activeInstances}
            icon={PlayArrowIcon}
            color="#2e7d32"
            tooltip="Currently running process instances"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Completed"
            value={stats.statusCounts[ProcessStatus.COMPLETED] || 0}
            icon={CheckCircleIcon}
            color="#1976d2"
            tooltip="Successfully completed process instances"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Errors"
            value={stats.statusCounts[ProcessStatus.ERROR] || 0}
            icon={ErrorIcon}
            color="#d32f2f"
            tooltip="Process instances that encountered errors"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Avg. Completion Time"
            value={formatDuration(stats.averageCompletionTime)}
            icon={AccessTimeIcon}
            color="#f57c00"
            tooltip="Average time to complete a process"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Error Rate"
            value={`${stats.errorRate.toFixed(1)}%`}
            icon={AssessmentIcon}
            color="#7b1fa2"
            tooltip="Percentage of processes that resulted in errors"
          />
        </Grid>
      </Grid>

      {/* TODO: Add recent activities list */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          Recent Activities
        </Typography>
        <Card>
          <CardContent>
            <Typography color="textSecondary">
              No recent activities to display.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
};

export default Dashboard;
