import { useState, useEffect, useCallback, useRef } from 'react';
import apiService from '@/services/api';
import { Token } from '@/types/process';

// Re-export the Token type as TokenData for consistency
export type TokenData = Token;

interface UseProcessTokensProps {
  instanceId: string | string[];
  enabled?: boolean;
  pollingInterval?: number;
}

export const useProcessTokens = ({
  instanceId,
  enabled = true,
  pollingInterval = 2000, // Default to 2 seconds
}: UseProcessTokensProps) => {
  const [tokens, setTokens] = useState<TokenData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const pollingTimeoutRef = useRef<number | undefined>(undefined);

  // Fetch token data
  const fetchTokens = useCallback(async () => {
    try {
      const instanceIds = Array.isArray(instanceId) ? instanceId : [instanceId];

      // Fetch tokens for all instances in parallel
      const responses = await Promise.all(
        instanceIds.map((id) => apiService.getInstanceTokens(id))
      );

      // Combine and map all tokens
      const allTokens = responses.flatMap((response) =>
        (response.data ?? []).map(
          (token): TokenData => ({
            nodeId: token.nodeId,
            state: token.state,
            scopeId: token.scopeId,
            data: token.data,
          })
        )
      );

      setTokens(allTokens);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error('Failed to fetch tokens')
      );
      console.error('Error fetching tokens:', err);
    } finally {
      setLoading(false);
    }
  }, [instanceId]);

  // Setup polling
  useEffect(() => {
    if (!enabled) {
      setTokens([]);
      setLoading(false);
      return;
    }

    // Initial fetch
    fetchTokens();

    // Setup polling interval
    const poll = () => {
      pollingTimeoutRef.current = window.setTimeout(() => {
        fetchTokens().then(() => poll());
      }, pollingInterval);
    };

    poll();

    // Cleanup
    return () => {
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
      }
    };
  }, [enabled, fetchTokens, pollingInterval]);

  return {
    tokens,
    loading,
    error,
    refetch: fetchTokens,
  };
};
