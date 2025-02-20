import { useState, useEffect, useCallback } from 'react';
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

  // Reset state when disabled
  useEffect(() => {
    if (!enabled) {
      setTokens([]);
      setLoading(false);
      setError(null);
    }
  }, [enabled]);

  // Setup polling with setInterval
  useEffect(() => {
    // Don't setup polling if disabled or no instanceId
    if (
      !enabled ||
      !instanceId ||
      (Array.isArray(instanceId) && instanceId.length === 0)
    ) {
      return;
    }

    let mounted = true;

    const pollTokens = async () => {
      try {
        const instanceIds = Array.isArray(instanceId)
          ? instanceId
          : [instanceId];

        // Fetch tokens for all instances in parallel
        const responses = await Promise.all(
          instanceIds.map((id) => apiService.getInstanceTokens(id))
        );

        // Only update state if component is still mounted
        if (mounted) {
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
          setLoading(false);
        }
      } catch (err) {
        if (mounted) {
          setError(
            err instanceof Error ? err : new Error('Failed to fetch tokens')
          );
          console.error('Error fetching tokens:', err);
          setLoading(false);
        }
      }
    };

    // Initial fetch
    pollTokens();

    // Setup polling interval
    const intervalId = setInterval(pollTokens, pollingInterval);

    // Cleanup
    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, [enabled, instanceId, pollingInterval]);

  return {
    tokens,
    loading,
    error,
    refetch: fetchTokens,
  };
};
