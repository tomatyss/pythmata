import { ReactNode } from 'react';
import { FieldError } from 'react-hook-form';

// DataTable Types
export interface Column<T> {
  id: string;
  label: string;
  minWidth?: number;
  align?: 'left' | 'right' | 'center';
  format?: (value: any) => ReactNode;
  getValue: (row: T) => any;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  error?: string | null;
  page?: number;
  pageSize?: number;
  totalItems?: number;
  onPageChange?: (newPage: number) => void;
  onPageSizeChange?: (newPageSize: number) => void;
  emptyMessage?: string;
}

// FormField Types
export interface FormFieldProps {
  label?: string;
  error?: FieldError;
  required?: boolean;
  fullWidth?: boolean;
  children: ReactNode;
  helperText?: string;
}

// Card Types
export interface CardProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  menu?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  noPadding?: boolean;
}

// StatsCard Types
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

// ErrorMessage Types
export interface ErrorMessageProps {
  message?: string;
  error?: Error | string;
  onRetry?: () => void;
  fullHeight?: boolean;
}

// LoadingSpinner Types
export interface LoadingSpinnerProps {
  message?: string;
  size?: number;
  fullHeight?: boolean;
}

// PageHeader Types
export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface PageHeaderProps {
  title: string;
  breadcrumbs?: BreadcrumbItem[];
  action?: ReactNode;
  description?: string;
}

// StatusChip Types
export interface StatusChipProps {
  status: string;
  size?: 'small' | 'medium';
}
