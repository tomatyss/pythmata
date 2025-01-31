import { ReactNode } from 'react';
import {
  Card as MuiCard,
  CardHeader,
  CardContent,
  CardActions,
  Typography,
  Box,
  IconButton,
  Divider,
} from '@mui/material';
import { MoreVert as MoreVertIcon } from '@mui/icons-material';

export interface CardProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  menu?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  noPadding?: boolean;
}

const Card = ({
  title,
  subtitle,
  action,
  menu,
  footer,
  children,
  noPadding = false,
}: CardProps) => {
  return (
    <MuiCard>
      <CardHeader
        title={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="h6" component="h2">
              {title}
            </Typography>
            {action}
          </Box>
        }
        subheader={subtitle}
        action={
          menu ? (
            <IconButton size="small" aria-label="more options">
              <MoreVertIcon />
            </IconButton>
          ) : undefined
        }
      />
      <Divider />
      <CardContent sx={{ p: noPadding ? 0 : undefined }}>
        {children}
      </CardContent>
      {footer && (
        <>
          <Divider />
          <CardActions>{footer}</CardActions>
        </>
      )}
    </MuiCard>
  );
};

export default Card;
