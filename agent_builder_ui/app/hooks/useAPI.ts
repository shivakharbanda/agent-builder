import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../lib/api';
import { APP_CONFIG } from '../lib/config';
import type { APIError, FormState, PaginatedResponse } from '../lib/types';

// Enhanced hook for API calls with better error handling and fallback data
export function useAPICall<T>(
  apiCall: () => Promise<T>,
  dependencies: any[] = [],
  options: {
    fallbackData?: T;
    enableRetry?: boolean;
    retryDelay?: number;
    maxRetries?: number;
    enableMockData?: boolean;
  } = {}
) {
  const [data, setData] = useState<T | null>(options.fallbackData || null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(true);
  const [retryCount, setRetryCount] = useState(0);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const {
    enableRetry = true,
    retryDelay = 2000,
    maxRetries = 3,
    enableMockData = APP_CONFIG.ENABLE_MOCK_DATA
  } = options;

  const execute = useCallback(async (isRetry = false) => {
    // Clear any existing retry timeout
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
    }

    try {
      if (!isRetry) {
        setLoading(true);
        setError(null);
      }

      // Check connectivity first
      const connected = await api.checkConnectivity();
      setIsConnected(connected);

      if (!connected && !enableMockData) {
        throw new Error('No connection to server. Please check your network.');
      }

      let result: T;
      if (!connected && enableMockData) {
        // Use mock data when offline
        result = getMockData<T>();
        if (APP_CONFIG.ENABLE_DEBUG) {
          console.warn('Using mock data due to connectivity issues');
        }
      } else {
        result = await apiCall();
      }

      setData(result);
      setRetryCount(0); // Reset retry count on success

      if (APP_CONFIG.ENABLE_DEBUG) {
        console.log('API call successful:', result);
      }
    } catch (err) {
      const apiError = err as APIError;
      const errorMessage = apiError.detail || apiError.message || 'An error occurred';

      if (APP_CONFIG.ENABLE_DEBUG) {
        console.error('API call failed:', apiError);
      }

      // Check if we should retry
      if (enableRetry && retryCount < maxRetries && isNetworkError(apiError)) {
        const nextRetryCount = retryCount + 1;
        setRetryCount(nextRetryCount);

        if (APP_CONFIG.ENABLE_DEBUG) {
          console.log(`Retrying API call (${nextRetryCount}/${maxRetries}) in ${retryDelay}ms`);
        }

        retryTimeoutRef.current = setTimeout(() => {
          execute(true);
        }, retryDelay * nextRetryCount);

        return; // Don't set error state yet, we're retrying
      }

      // If we have fallback data and this is a network error, use fallback
      if (options.fallbackData && isNetworkError(apiError)) {
        setData(options.fallbackData);
        setError(`Using cached data. ${errorMessage}`);
      } else {
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  }, [...dependencies, retryCount]);

  useEffect(() => {
    execute();

    // Cleanup timeout on unmount
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, [execute]);

  const refetch = useCallback(() => {
    setRetryCount(0);
    execute();
  }, [execute]);

  return {
    data,
    loading,
    error,
    isConnected,
    retryCount,
    refetch
  };
}

// Helper function to determine if error is network-related
function isNetworkError(error: APIError): boolean {
  return !!(
    error.code === 'NETWORK_ERROR' ||
    error.code === 'ECONNABORTED' ||
    error.status === 0 ||
    error.detail?.includes('network') ||
    error.detail?.includes('connection')
  );
}

// Helper function to generate mock data based on type
function getMockData<T>(): T {
  // Basic mock data structure
  const mockPaginatedResponse = {
    count: 0,
    next: null,
    previous: null,
    results: []
  };

  return mockPaginatedResponse as T;
}

// Hook for form submissions
export function useFormSubmit<T, D>(
  submitFunction: (data: D) => Promise<T>
) {
  const [state, setState] = useState<FormState>({
    loading: false,
    error: null,
    success: false,
  });

  const submit = useCallback(async (data: D) => {
    setState({ loading: true, error: null, success: false });
    try {
      const result = await submitFunction(data);
      setState({ loading: false, error: null, success: true });
      return result;
    } catch (err) {
      const apiError = err as APIError;
      setState({
        loading: false,
        error: apiError.detail || 'An error occurred',
        success: false
      });
      throw err;
    }
  }, [submitFunction]);

  const reset = useCallback(() => {
    setState({ loading: false, error: null, success: false });
  }, []);

  return { ...state, submit, reset };
}

// Specific hooks for each resource
export function useProjects() {
  return useAPICall(() => api.getProjects());
}

export function useProject(id: number) {
  return useAPICall(() => api.getProject(id), [id]);
}

export function useAgents(projectId?: number) {
  return useAPICall(() => api.getAgents(projectId), [projectId]);
}

export function useAgent(id: number) {
  return useAPICall(() => api.getAgent(id), [id]);
}

export function useAgentPrompts(id: number) {
  return useAPICall(() => api.getAgentPrompts(id), [id]);
}

export function useAgentTools(id: number) {
  return useAPICall(() => api.getAgentTools(id), [id]);
}

export function useTools() {
  return useAPICall(() => api.getTools());
}

export function useWorkflows(projectId?: number) {
  const fallbackData = {
    count: 0,
    next: null,
    previous: null,
    results: []
  };

  return useAPICall(
    () => api.getWorkflows(projectId),
    [projectId],
    {
      fallbackData,
      enableRetry: true,
      maxRetries: 3,
      retryDelay: 2000
    }
  );
}

export function useWorkflow(id: number) {
  const fallbackData = {
    id,
    name: 'Unknown Workflow',
    description: 'Workflow data unavailable',
    project: 0,
    configuration: {},
    status: 'draft' as const,
    nodes: [],
    output_nodes: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    created_by: 0,
    is_active: true
  };

  return useAPICall(
    () => api.getWorkflow(id),
    [id],
    {
      fallbackData,
      enableRetry: true,
      maxRetries: 2
    }
  );
}

export function useDataSources() {
  return useAPICall(() => api.getDataSources());
}

// Credential hooks
export function useCredentialCategories() {
  return useAPICall(() => api.getCredentialCategories());
}

export function useCredentialTypes(categoryId?: number) {
  return useAPICall(() => api.getCredentialTypes(categoryId), [categoryId]);
}

export function useCredentialType(id: number) {
  return useAPICall(() => api.getCredentialType(id), [id]);
}

export function useCredentialTypeFields(id: number | null) {
  return useAPICall(() => {
    if (!id || id <= 0) {
      return Promise.resolve([]);
    }
    return api.getCredentialTypeFields(id);
  }, [id]);
}

export function useCredentials() {
  return useAPICall(() => api.getCredentials());
}

export function useCredential(id: number) {
  return useAPICall(() => api.getCredential(id), [id]);
}

// Hook for managing local storage
export function useLocalStorage<T>(key: string, defaultValue: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      if (typeof window !== 'undefined') {
        const item = window.localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
      }
      return defaultValue;
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error);
      return defaultValue;
    }
  });

  const setStoredValue = useCallback((newValue: T | ((val: T) => T)) => {
    try {
      const valueToStore = newValue instanceof Function ? newValue(value) : newValue;
      setValue(valueToStore);
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }
    } catch (error) {
      console.error(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, value]);

  return [value, setStoredValue] as const;
}

// Hook for debounced values
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Hook for managing async state
export function useAsync<T>() {
  const [state, setState] = useState<{
    data: T | null;
    loading: boolean;
    error: string | null;
  }>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(async (asyncFunction: () => Promise<T>) => {
    setState({ data: null, loading: true, error: null });
    try {
      const result = await asyncFunction();
      setState({ data: result, loading: false, error: null });
      return result;
    } catch (err) {
      const apiError = err as APIError;
      const error = apiError.detail || 'An error occurred';
      setState({ data: null, loading: false, error });
      throw err;
    }
  }, []);

  return { ...state, execute };
}

// Hook for pagination
export function usePagination<T>(
  fetchFunction: (page: number) => Promise<{ results: T[]; count: number; next: string | null; previous: string | null }>
) {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);

  const loadPage = useCallback(async (pageNumber: number, append = false) => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetchFunction(pageNumber);

      if (append) {
        setData(prev => [...prev, ...result.results]);
      } else {
        setData(result.results);
      }

      setTotal(result.count);
      setHasMore(!!result.next);
      setPage(pageNumber);
    } catch (err) {
      const apiError = err as APIError;
      setError(apiError.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [fetchFunction]);

  const loadMore = useCallback(() => {
    if (hasMore && !loading) {
      loadPage(page + 1, true);
    }
  }, [hasMore, loading, page, loadPage]);

  const refresh = useCallback(() => {
    loadPage(1, false);
  }, [loadPage]);

  useEffect(() => {
    loadPage(1, false);
  }, [loadPage]);

  return {
    data,
    loading,
    error,
    page,
    hasMore,
    total,
    loadMore,
    refresh,
  };
}