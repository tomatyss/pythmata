import { QueryClient } from '@tanstack/react-query';

/**
 * Creates and configures a QueryClient instance for React Query.
 * @returns {QueryClient} Configured QueryClient instance.
 */
const createQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: 1,
        staleTime: 5 * 60 * 1000, // 5 minutes
      },
    },
  });
};

export default createQueryClient;
