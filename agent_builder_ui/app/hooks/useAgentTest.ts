import { useState, useCallback } from 'react';
import { api } from '../lib/api';
import type {
  AgentTestRequest,
  AgentTestResponse,
  ConversationMessage,
  InternalToolAttachment
} from '../lib/types';

interface UseAgentTestResult {
  testing: boolean;
  error: string | null;
  testResult: AgentTestResponse | null;
  conversationHistory: ConversationMessage[];
  runStructuredTest: (inputs: Record<string, any>, credentialId: number, model?: string, mcpServerIds?: number[], internalToolAttachments?: InternalToolAttachment[]) => Promise<void>;
  runUnstructuredTest: (message: string, credentialId: number, model?: string, mcpServerIds?: number[], internalToolAttachments?: InternalToolAttachment[]) => Promise<void>;
  clearConversation: () => void;
  clearResults: () => void;
}

export const useAgentTest = (agentId: number): UseAgentTestResult => {
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<AgentTestResponse | null>(null);
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);

  const runStructuredTest = useCallback(async (
    inputs: Record<string, any>,
    credentialId: number,
    model?: string,
    mcpServerIds?: number[],
    internalToolAttachments?: InternalToolAttachment[]
  ) => {
    try {
      setTesting(true);
      setError(null);
      setTestResult(null);

      const request: AgentTestRequest = {
        test_type: 'structured',
        credential_id: credentialId,
        model,
        inputs,
        mcp_server_ids: mcpServerIds,
        internal_tool_attachments: internalToolAttachments
      };

      const result = await api.testAgent(agentId, request);
      setTestResult(result);

      if (!result.success && result.error) {
        setError(result.error);
      }
    } catch (err: any) {
      setError(err.detail || 'Failed to run test');
      console.error('Failed to run structured test:', err);
    } finally {
      setTesting(false);
    }
  }, [agentId]);

  const runUnstructuredTest = useCallback(async (
    message: string,
    credentialId: number,
    model?: string,
    mcpServerIds?: number[],
    internalToolAttachments?: InternalToolAttachment[]
  ) => {
    try {
      setTesting(true);
      setError(null);

      const request: AgentTestRequest = {
        test_type: 'unstructured',
        credential_id: credentialId,
        model,
        message,
        conversation_history: conversationHistory,
        mcp_server_ids: mcpServerIds,
        internal_tool_attachments: internalToolAttachments
      };

      const result = await api.testAgent(agentId, request);
      setTestResult(result);

      if (result.success && result.conversation_history) {
        setConversationHistory(result.conversation_history);
      } else if (!result.success && result.error) {
        setError(result.error);
      }
    } catch (err: any) {
      setError(err.detail || 'Failed to run test');
      console.error('Failed to run unstructured test:', err);
    } finally {
      setTesting(false);
    }
  }, [agentId, conversationHistory]);

  const clearConversation = useCallback(() => {
    setConversationHistory([]);
    setTestResult(null);
    setError(null);
  }, []);

  const clearResults = useCallback(() => {
    setTestResult(null);
    setError(null);
  }, []);

  return {
    testing,
    error,
    testResult,
    conversationHistory,
    runStructuredTest,
    runUnstructuredTest,
    clearConversation,
    clearResults
  };
};
