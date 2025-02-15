import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import apiService from '@/services/api';
import { formatDate } from '@/utils/date';
import {
  Box,
  Typography,
  IconButton,
  Chip,
  CircularProgress,
  Breadcrumbs,
  Link,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import {
  Visibility as VisibilityIcon,
  PlayArrow as PlayArrowIcon,
  Pause as PauseIcon,
} from '@mui/icons-material';

interface ProcessInstance {
  id: string;
  definitionId: string;
  definitionName: string;
  status: string;
  startTime: string;
  endTime?: string;
}

const ProcessInstanceList = () => {
  const navigate = useNavigate();
  const { id: processId } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [instances, setInstances] = useState<ProcessInstance[]>([]);
  const [processName, setProcessName] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const columns: GridColDef[] = [
    { field: 'id', headerName: 'ID', flex: 1 },
    {
      field: 'definitionName',
      headerName: 'Process',
      flex: 1,
      hideable: !!processId,
    },
    {
      field: 'status',
      headerName: 'Status',
      flex: 0.5,
      renderCell: (params: GridRenderCellParams<ProcessInstance>) => (
        <Chip
          label={params.value}
          color={
            params.value === 'RUNNING'
              ? 'primary'
              : params.value === 'COMPLETED'
                ? 'success'
                : params.value === 'ERROR'
                  ? 'error'
                  : 'default'
          }
          size="small"
        />
      ),
    },
    {
      field: 'startTime',
      headerName: 'Start Time',
      flex: 1,
      renderCell: (params: GridRenderCellParams<ProcessInstance>) =>
        formatDate(params.value as string),
    },
    {
      field: 'endTime',
      headerName: 'End Time',
      flex: 1,
      renderCell: (params: GridRenderCellParams<ProcessInstance>) =>
        params.value ? formatDate(params.value as string) : 'In Progress',
    },
    {
      field: 'actions',
      headerName: 'Actions',
      flex: 0.5,
      sortable: false,
      renderCell: (params: GridRenderCellParams<ProcessInstance>) => (
        <Box>
          <IconButton
            onClick={() => handleViewInstance(params.row.id)}
            title="View Instance"
          >
            <VisibilityIcon />
          </IconButton>
          {params.row.status === 'RUNNING' && (
            <IconButton
              onClick={() => handleSuspendInstance(params.row.id)}
              title="Suspend Instance"
            >
              <PauseIcon />
            </IconButton>
          )}
          {params.row.status === 'SUSPENDED' && (
            <IconButton
              onClick={() => handleResumeInstance(params.row.id)}
              title="Resume Instance"
            >
              <PlayArrowIcon />
            </IconButton>
          )}
        </Box>
      ),
    },
  ];

  const fetchData = useCallback(async () => {
    try {
      if (!processId) {
        console.error('No process ID provided');
        return;
      }
      setLoading(true);
      console.warn('Fetching instances with params:', {
        definition_id: processId,
        page: page + 1,
        page_size: pageSize,
        status: statusFilter === 'all' ? undefined : statusFilter,
      });
      const [instancesResponse, processResponse] = await Promise.all([
        apiService.getProcessInstances({
          definition_id: processId,
          page: page + 1,
          page_size: pageSize,
          status: statusFilter === 'all' ? undefined : statusFilter,
        }),
        processId ? apiService.getProcessDefinition(processId) : null,
      ]);

      if (processResponse) {
        setProcessName(processResponse.data.name);
      }

      setInstances(instancesResponse.data.items);
      setTotalCount(instancesResponse.data.total);
    } catch (error) {
      console.error('Failed to fetch instances:', error);
    } finally {
      setLoading(false);
    }
  }, [processId, page, pageSize, statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleViewInstance = (instanceId: string) => {
    navigate(`/processes/${processId}/instances/${instanceId}`);
  };

  const handleSuspendInstance = async (instanceId: string) => {
    try {
      await apiService.suspendProcessInstance(instanceId);
      // Refresh instances list with all current parameters
      console.warn('Refreshing after suspend with params:', {
        definition_id: processId,
        page: page + 1,
        page_size: pageSize,
        status: statusFilter === 'all' ? undefined : statusFilter,
      });
      const response = await apiService.getProcessInstances({
        definition_id: processId,
        page: page + 1,
        page_size: pageSize,
        status: statusFilter === 'all' ? undefined : statusFilter,
      });
      setInstances(response.data.items);
      setTotalCount(response.data.total);
    } catch (error) {
      console.error('Failed to suspend instance:', error);
    }
  };

  const handleResumeInstance = async (instanceId: string) => {
    try {
      await apiService.resumeProcessInstance(instanceId);
      // Refresh instances list with all current parameters
      console.warn('Refreshing after resume with params:', {
        definition_id: processId,
        page: page + 1,
        page_size: pageSize,
        status: statusFilter === 'all' ? undefined : statusFilter,
      });
      const response = await apiService.getProcessInstances({
        definition_id: processId,
        page: page + 1,
        page_size: pageSize,
        status: statusFilter === 'all' ? undefined : statusFilter,
      });
      setInstances(response.data.items);
      setTotalCount(response.data.total);
    } catch (error) {
      console.error('Failed to resume instance:', error);
    }
  };

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
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link
          color="inherit"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate('/processes');
          }}
        >
          Processes
        </Link>
        {processId && (
          <Link
            color="inherit"
            href="#"
            onClick={(e) => {
              e.preventDefault();
              navigate(`/processes/${processId}`);
            }}
          >
            {processName}
          </Link>
        )}
        <Typography color="text.primary">Instances</Typography>
      </Breadcrumbs>

      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 4,
        }}
      >
        <Typography variant="h4">
          Process Instances {processName ? `- ${processName}` : ''}
        </Typography>
        <FormControl sx={{ minWidth: 120 }}>
          <InputLabel>Status</InputLabel>
          <Select
            value={statusFilter}
            label="Status"
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="running">Running</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="suspended">Suspended</MenuItem>
            <MenuItem value="error">Error</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Box sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={instances}
          columns={columns}
          pagination
          paginationMode="server"
          rowCount={totalCount}
          loading={loading}
          paginationModel={{
            page,
            pageSize,
          }}
          onPaginationModelChange={(model) => {
            setPage(model.page);
            setPageSize(model.pageSize);
          }}
          disableRowSelectionOnClick
          disableColumnMenu
          sx={{
            '& .MuiDataGrid-cell': {
              borderBottom: 1,
              borderColor: 'divider',
            },
          }}
        />
      </Box>
    </Box>
  );
};

export default ProcessInstanceList;
