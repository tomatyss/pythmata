import { Chip, ChipProps } from '@mui/material';
import {
  PlayArrow as RunningIcon,
  CheckCircle as CompletedIcon,
  Pause as SuspendedIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { ProcessStatus } from '@/types/process';

interface StatusChipProps extends Omit<ChipProps, 'color'> {
  status: ProcessStatus | string;
  size?: 'small' | 'medium';
}

const StatusChip = ({ status, size = 'small', ...props }: StatusChipProps) => {
  const getStatusConfig = (status: string) => {
    switch (status.toUpperCase()) {
      case ProcessStatus.RUNNING:
        return {
          label: 'Running',
          color: 'primary' as const,
          icon: <RunningIcon />,
        };
      case ProcessStatus.COMPLETED:
        return {
          label: 'Completed',
          color: 'success' as const,
          icon: <CompletedIcon />,
        };
      case ProcessStatus.SUSPENDED:
        return {
          label: 'Suspended',
          color: 'warning' as const,
          icon: <SuspendedIcon />,
        };
      case ProcessStatus.ERROR:
        return {
          label: 'Error',
          color: 'error' as const,
          icon: <ErrorIcon />,
        };
      default:
        return {
          label: status,
          color: 'default' as const,
          icon: undefined,
        };
    }
  };

  const { label, color, icon } = getStatusConfig(status);

  return (
    <Chip
      label={label}
      color={color}
      icon={icon}
      size={size}
      variant="filled"
      {...props}
    />
  );
};

export default StatusChip;
