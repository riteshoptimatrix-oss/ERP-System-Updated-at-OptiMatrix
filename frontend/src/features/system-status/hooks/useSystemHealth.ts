'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/services/api-client';
import { LivenessData, ReadinessData } from '@/types/api';

interface UseSystemHealthReturn {
  liveness: LivenessData | null;
  readiness: ReadinessData | null;
  isLoading: boolean;
  error: string | null;
  lastChecked: Date | null;
  refetch: () => Promise<void>;
}

export function useSystemHealth(): UseSystemHealthReturn {
  const [liveness, setLiveness] = useState<LivenessData | null>(null);
  const [readiness, setReadiness] = useState<ReadinessData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [liveRes, readyRes] = await Promise.all([
        apiClient.get<LivenessData>('/api/v1/health'),
        apiClient.get<ReadinessData>('/api/v1/health/ready'),
      ]);

      if (liveRes.data) {
        setLiveness(liveRes.data);
      } else if (liveRes.error) {
        setError(`Liveness check failed: ${liveRes.error.message}`);
      }

      if (readyRes.data) {
        setReadiness(readyRes.data);
      } else if (readyRes.error) {
        // If 503, response body contains readiness failure details
        setError((prev) => prev ? `${prev} | Readiness: ${readyRes.error?.message}` : (readyRes.error?.message || 'Backend not ready'));
      }

      setLastChecked(new Date());
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to connect to backend services';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const runCheck = async () => {
      try {
        const [liveRes, readyRes] = await Promise.all([
          apiClient.get<LivenessData>('/api/v1/health'),
          apiClient.get<ReadinessData>('/api/v1/health/ready'),
        ]);

        if (!isMounted) return;

        if (liveRes.data) {
          setLiveness(liveRes.data);
        } else if (liveRes.error) {
          setError(`Liveness check failed: ${liveRes.error.message}`);
        }

        if (readyRes.data) {
          setReadiness(readyRes.data);
        } else if (readyRes.error) {
          setError((prev) =>
            prev
              ? `${prev} | Readiness: ${readyRes.error?.message}`
              : (readyRes.error?.message || 'Backend not ready')
          );
        }

        setLastChecked(new Date());
      } catch (err: unknown) {
        if (!isMounted) return;
        const msg = err instanceof Error ? err.message : 'Failed to connect to backend services';
        setError(msg);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    runCheck();
    const interval = setInterval(runCheck, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return {
    liveness,
    readiness,
    isLoading,
    error,
    lastChecked,
    refetch: fetchHealth,
  };
}
