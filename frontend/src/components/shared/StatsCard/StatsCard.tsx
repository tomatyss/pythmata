import { ReactNode } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
} from '@mui/material';

export interface StatsCardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  iconColor?: string;
  trend?: {
    value: number;
    label: string;
    isPositive: boolean;
  };
}

const StatsCard = ({
  title,
  value,
  icon,
  iconColor = 'primary.main',
  trend,
}: StatsCardProps) => {
  return (
    <Card>
      <CardContent>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
          }}
        >
          <Box>
            <Typography
              variant="subtitle2"
              color="textSecondary"
              gutterBottom
            >
              {title}
            </Typography>
            <Typography variant="h4">{value}</Typography>
            {trend && (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  mt: 1,
                  gap: 0.5,
                }}
              >
                <Typography
                  variant="body2"
                  color={trend.isPositive ? 'success.main' : 'error.main'}
                >
                  {trend.isPositive ? '+' : '-'}
                  {Math.abs(trend.value)}%
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  {trend.label}
                </Typography>
              </Box>
            )}
          </Box>
          {icon && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 48,
                height: 48,
                borderRadius: 1,
                bgcolor: `${iconColor}15`,
                color: iconColor,
              }}
            >
              {icon}
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default StatsCard;
