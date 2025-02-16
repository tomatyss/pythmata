import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';

interface ProcessInstance {
  id: string;
  startDate: string;
  endDate?: string;
  state: string;
  version: string;
  parentInstanceId?: string;
}

interface ProcessInstanceTableProps {
  instances: ProcessInstance[];
  onSelectInstance?: (instanceId: string) => void;
}

/**
 * A table component that displays process instances in Camunda style
 * @param props Component properties including instance data
 * @returns ProcessInstanceTable component
 */
const ProcessInstanceTable = ({
  instances,
  onSelectInstance,
}: ProcessInstanceTableProps) => {
  return (
    <Box sx={{ mt: 2 }}>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Instance ID</TableCell>
              <TableCell>Version</TableCell>
              <TableCell>Start Date</TableCell>
              <TableCell>End Date</TableCell>
              <TableCell>Parent Instance</TableCell>
              <TableCell align="right">Operations</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {instances.map((instance) => (
              <TableRow
                key={instance.id}
                sx={{
                  cursor: onSelectInstance ? 'pointer' : 'default',
                  '&:hover': {
                    backgroundColor: onSelectInstance ? '#f5f5f5' : 'inherit',
                  },
                }}
                onClick={() => onSelectInstance?.(instance.id)}
              >
                <TableCell component="th" scope="row">
                  {instance.id}
                </TableCell>
                <TableCell>{instance.version}</TableCell>
                <TableCell>
                  {new Date(instance.startDate).toLocaleString()}
                </TableCell>
                <TableCell>
                  {instance.endDate
                    ? new Date(instance.endDate).toLocaleString()
                    : '--'}
                </TableCell>
                <TableCell>{instance.parentInstanceId || 'None'}</TableCell>
                <TableCell align="right">
                  {/* Add operation buttons here if needed */}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default ProcessInstanceTable;
