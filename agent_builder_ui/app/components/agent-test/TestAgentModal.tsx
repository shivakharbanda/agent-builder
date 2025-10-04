import React, { useState, useEffect, useMemo } from 'react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Select, Input } from '../ui/Input';
import { LoadingState } from '../ui/Loading';
import { StructuredTestForm } from './StructuredTestForm';
import { UnstructuredTestChat } from './UnstructuredTestChat';
import { useAgentTest } from '../../hooks/useAgentTest';
import { api } from '../../lib/api';
import type { Agent, Prompt, Credential } from '../../lib/types';

interface TestAgentModalProps {
  agent: Agent;
  prompts: Prompt[];
  onClose: () => void;
}

export function TestAgentModal({ agent, prompts, onClose }: TestAgentModalProps) {
  const {
    testing,
    error,
    testResult,
    conversationHistory,
    runStructuredTest,
    runUnstructuredTest,
    clearConversation,
    clearResults
  } = useAgentTest(agent.id);

  // Extract placeholders from prompts locally (no API call needed)
  const placeholders = useMemo(() => {
    const found = new Set<string>();
    prompts.forEach(prompt => {
      const matches = prompt.content.matchAll(/\{\{(\w+)\}\}/g);
      for (const match of matches) {
        found.add(match[1]);
      }
    });
    return Array.from(found).sort();
  }, [prompts]);

  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loadingCredentials, setLoadingCredentials] = useState(true);
  const [selectedCredentialId, setSelectedCredentialId] = useState<number>(0);
  const [model, setModel] = useState<string>('gemini-1.5-flash');

  // Load LLM credentials
  useEffect(() => {
    const loadCredentials = async () => {
      try {
        setLoadingCredentials(true);
        const response = await api.getCredentials();
        // Filter for LLM credentials only
        const llmCredentials = response.results.filter(
          (cred) => cred.credential_type_name?.toLowerCase().includes('llm') ||
                     cred.credential_type_name?.toLowerCase().includes('openai') ||
                     cred.credential_type_name?.toLowerCase().includes('gemini')
        );
        setCredentials(llmCredentials);

        // Auto-select first credential if available
        if (llmCredentials.length > 0) {
          setSelectedCredentialId(llmCredentials[0].id);
        }
      } catch (err) {
        console.error('Failed to load credentials:', err);
      } finally {
        setLoadingCredentials(false);
      }
    };

    loadCredentials();
  }, []);

  const handleRunStructured = async (inputs: Record<string, any>) => {
    if (!selectedCredentialId || !model.trim()) return;
    await runStructuredTest(inputs, selectedCredentialId, model);
  };

  const handleSendMessage = async (message: string) => {
    if (!selectedCredentialId || !model.trim()) return;
    await runUnstructuredTest(message, selectedCredentialId, model);
  };

  if (loadingCredentials) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-[#1a2633] rounded-lg p-8 max-w-3xl w-full mx-4">
          <LoadingState>Loading credentials...</LoadingState>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[#1a2633] rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#374151]">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-[#1173d4] text-2xl">
                  science
                </span>
                <h2 className="text-xl font-bold text-white">Test Agent: {agent.name}</h2>
              </div>
              <p className="text-gray-400 text-sm mt-1">{agent.description}</p>
              <div className="flex items-center gap-2 mt-2">
                <Badge status={agent.return_type}>
                  {agent.return_type}
                </Badge>
                {placeholders.length > 0 && (
                  <span className="text-xs text-gray-500">
                    {placeholders.length} placeholder{placeholders.length > 1 ? 's' : ''}
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>
        </div>

        {/* Configuration */}
        <div className="px-6 py-4 bg-[#111a22] border-b border-[#374151]">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-4">
              <span className="material-symbols-outlined text-gray-400">key</span>
              <div className="flex-1">
                <Select
                  label="LLM Credential"
                  value={selectedCredentialId}
                  onChange={(e) => setSelectedCredentialId(parseInt(e.target.value))}
                  options={[
                    { value: 0, label: 'Select a credential', disabled: true },
                    ...credentials.map(cred => ({
                      value: cred.id,
                      label: `${cred.name} (${cred.credential_type_name})`
                    }))
                  ]}
                  required
                />
                {credentials.length === 0 && (
                  <p className="text-yellow-400 text-xs mt-2">
                    ⚠️ No LLM credentials found. Please create one in the Credentials section.
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="material-symbols-outlined text-gray-400">psychology</span>
              <div className="flex-1">
                <Input
                  label="Model Name"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="e.g., gemini-1.5-flash, gpt-4o"
                  required
                />
                <p className="text-gray-500 text-xs mt-1">
                  Common: gemini-1.5-flash, gemini-1.5-pro, gpt-4o, gpt-4o-mini
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6">
          {agent.return_type === 'structured' ? (
            <StructuredTestForm
              placeholders={placeholders}
              credentialId={selectedCredentialId}
              model={model}
              onRun={handleRunStructured}
              testing={testing}
              testResult={testResult}
              error={error}
            />
          ) : (
            <UnstructuredTestChat
              credentialId={selectedCredentialId}
              model={model}
              conversationHistory={conversationHistory}
              onSendMessage={handleSendMessage}
              onClearConversation={clearConversation}
              testing={testing}
              error={error}
            />
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#374151] flex justify-end gap-3">
          {agent.return_type === 'structured' && testResult && (
            <Button
              variant="outline"
              onClick={clearResults}
            >
              Clear Results
            </Button>
          )}
          <Button
            variant="outline"
            onClick={onClose}
          >
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
