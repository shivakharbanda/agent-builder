import { useCallback } from 'react';
import { api } from '../lib/api';

export interface ExecutionPollCallbacks {
  onProgress?: (status: string, progressPercentage: number, progressMessage: string) => void;
  onComplete?: (results: any) => void;
  onError?: (error: string) => void;
}

export const useExecutionPolling = () => {
  const pollExecution = useCallback(async (
    executionId: number,
    callbacks: ExecutionPollCallbacks = {}
  ) => {
    const { onProgress, onComplete, onError } = callbacks;

    const poll = async () => {
      try {
        const status = await api.getExecutionStatus(executionId);

        // Call progress callback
        if (onProgress) {
          onProgress(
            status.status,
            status.progress_percentage || 0,
            status.progress_message || ''
          );
        }

        // Check if execution is complete
        if (status.is_complete) {
          if (status.status === 'completed') {
            onComplete?.(status);
          } else {
            onError?.(status.error_message || 'Execution failed');
          }
          return; // Stop polling
        }

        // Continue polling after 2 seconds
        setTimeout(poll, 2000);
      } catch (error: any) {
        onError?.(error.message || 'Failed to poll execution status');
      }
    };

    // Start polling
    poll();
  }, []);

  return { pollExecution };
};
