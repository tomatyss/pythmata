import { useState, useCallback } from 'react';
import { formatError } from '@/utils';

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface UseAsyncOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
  initialData?: T;
}

const useAsync = <T>(options: UseAsyncOptions<T> = {}) => {
  const [state, setState] = useState<AsyncState<T>>({
    data: options.initialData || null,
    loading: false,
    error: null,
  });

  const execute = useCallback(
    async (asyncFunction: () => Promise<T>) => {
      try {
        setState((prev) => ({ ...prev, loading: true, error: null }));
        const data = await asyncFunction();
        setState({ data, loading: false, error: null });
        options.onSuccess?.(data);
        return data;
      } catch (error) {
        const errorMessage = formatError(error);
        setState({ data: null, loading: false, error: errorMessage });
        options.onError?.(error as Error);
        throw error;
      }
    },
    [options]
  );

  const reset = useCallback(() => {
    setState({
      data: options.initialData || null,
      loading: false,
      error: null,
    });
  }, [options.initialData]);

  return {
    ...state,
    execute,
    reset,
    setData: useCallback(
      (data: T) => setState((prev) => ({ ...prev, data })),
      []
    ),
    setError: useCallback(
      (error: string) =>
        setState((prev) => ({ ...prev, error, loading: false })),
      []
    ),
  };
};

interface PaginatedData<T> {
  items: T[];
  total: number;
}

// Helper hook for paginated data
export const usePaginatedAsync = <T>(
  options: UseAsyncOptions<PaginatedData<T>> = {}
) => {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  const asyncState = useAsync<PaginatedData<T>>({
    ...options,
    onSuccess: (data) => {
      if (data?.total !== undefined) {
        setTotal(data.total);
      }
      options.onSuccess?.(data);
    },
  });

  return {
    ...asyncState,
    pagination: {
      page,
      pageSize,
      total,
      setPage,
      setPageSize,
      totalPages: Math.ceil(total / pageSize),
    },
  };
};

export default useAsync;
