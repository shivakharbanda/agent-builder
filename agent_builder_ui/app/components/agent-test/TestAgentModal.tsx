import React, { useState, useEffect, useMemo } from 'react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Select, Input } from '../ui/Input';
import { LoadingState } from '../ui/Loading';
import { StructuredTestForm } from './StructuredTestForm';
import { UnstructuredTestChat } from './UnstructuredTestChat';
import { useAgentTest } from '../../hooks/useAgentTest';
import { useInternalTools } from '../../hooks/useAPI';
import { api } from '../../lib/api';
import type { Agent, Prompt, Credential, InternalTool, InternalToolAttachment } from '../../lib/types';

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

  const [llmCredentials, setLlmCredentials] = useState<Credential[]>([]);
  const [allCredentials, setAllCredentials] = useState<Credential[]>([]);
  const [loadingCredentials, setLoadingCredentials] = useState(true);
  const [selectedCredentialId, setSelectedCredentialId] = useState<number>(0);
  const [model, setModel] = useState<string>('gemini-1.5-flash');
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [selectedMcpServerIds, setSelectedMcpServerIds] = useState<number[]>([]);
  const [selectedInternalTools, setSelectedInternalTools] = useState<Map<number, number>>(new Map());

  // Load internal tools
  const { data: internalToolsData, loading: loadingInternalTools } = useInternalTools();

  // Load credentials and MCP servers
  useEffect(() => {
    const loadCredentials = async () => {
      try {
        setLoadingCredentials(true);
        const response = await api.getCredentials();

        // Store all credentials for internal tools
        setAllCredentials(response.results);

        // Filter for LLM credentials
        const llmCreds = response.results.filter(
          (cred) => cred.credential_type_name?.toLowerCase().includes('llm') ||
                     cred.credential_type_name?.toLowerCase().includes('openai') ||
                     cred.credential_type_name?.toLowerCase().includes('gemini')
        );
        setLlmCredentials(llmCreds);

        // Auto-select first LLM credential if available
        if (llmCreds.length > 0) {
          setSelectedCredentialId(llmCreds[0].id);
        }
      } catch (err) {
        console.error('Failed to load credentials:', err);
      } finally {
        setLoadingCredentials(false);
      }
    };

    const loadMcpServers = async () => {
      try {
        const response = await api.getMCPServers();
        setMcpServers(response.results || []);
      } catch (err) {
        console.error('Failed to load MCP servers:', err);
      }
    };

    loadCredentials();
    loadMcpServers();
  }, []);

  const handleRunStructured = async (inputs: Record<string, any>) => {
    if (!selectedCredentialId || !model.trim()) return;

    // Convert internal tools map to attachments array
    const internalToolAttachments: InternalToolAttachment[] = Array.from(selectedInternalTools.entries()).map(
      ([tool_id, credential_id]) => ({ tool_id, credential_id })
    );

    await runStructuredTest(inputs, selectedCredentialId, model, selectedMcpServerIds, internalToolAttachments);
  };

  const handleSendMessage = async (message: string) => {
    if (!selectedCredentialId || !model.trim()) return;

    // Convert internal tools map to attachments array
    const internalToolAttachments: InternalToolAttachment[] = Array.from(selectedInternalTools.entries()).map(
      ([tool_id, credential_id]) => ({ tool_id, credential_id })
    );

    await runUnstructuredTest(message, selectedCredentialId, model, selectedMcpServerIds, internalToolAttachments);
  };

  const toggleMcpServer = (serverId: number) => {
    setSelectedMcpServerIds(prev =>
      prev.includes(serverId)
        ? prev.filter(id => id !== serverId)
        : [...prev, serverId]
    );
  };

  const toggleInternalTool = (toolId: number, tool: InternalTool) => {
    setSelectedInternalTools(prev => {
      const newMap = new Map(prev);
      if (newMap.has(toolId)) {
        newMap.delete(toolId);
      } else {
        // Auto-select first matching credential if available
        const matchingCreds = allCredentials.filter(
          cred => tool.required_credential_type && cred.credential_type === tool.required_credential_type
        );
        const defaultCredId = matchingCreds.length > 0 ? matchingCreds[0].id : 0;
        newMap.set(toolId, defaultCredId);
      }
      return newMap;
    });
  };

  const updateInternalToolCredential = (toolId: number, credentialId: number) => {
    setSelectedInternalTools(prev => {
      const newMap = new Map(prev);
      newMap.set(toolId, credentialId);
      return newMap;
    });
  };

  const getCredentialsForTool = (tool: InternalTool): Credential[] => {
    if (!tool.requires_credential || !tool.required_credential_type) {
      return allCredentials;
    }
    return allCredentials.filter(
      cred => cred.credential_type === tool.required_credential_type
    );
  };

  const internalTools = internalToolsData?.results || [];

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

        {/* Configuration + Content Side-by-Side */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left: Configuration Panel */}
          <div className="w-2/5 border-r border-[#374151] overflow-y-auto p-6 bg-[#111a22]">
            <h3 className="text-white font-medium mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined">settings</span>
              Configuration
            </h3>

            <div className="space-y-4">
              {/* LLM Credential */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-gray-400 text-sm">key</span>
                  <label className="text-sm text-gray-300 font-medium">LLM Credential</label>
                </div>
                <Select
                  label=""
                  value={selectedCredentialId}
                  onChange={(e) => setSelectedCredentialId(parseInt(e.target.value))}
                  options={[
                    { value: 0, label: 'Select a credential', disabled: true },
                    ...llmCredentials.map(cred => ({
                      value: cred.id,
                      label: `${cred.name} (${cred.credential_type_name})`
                    }))
                  ]}
                  required
                />
                {llmCredentials.length === 0 && (
                  <p className="text-yellow-400 text-xs mt-2">
                    ⚠️ No LLM credentials found. Please create one in the Credentials section.
                  </p>
                )}
              </div>

              {/* Model Name */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-gray-400 text-sm">psychology</span>
                  <label className="text-sm text-gray-300 font-medium">Model Name</label>
                </div>
                <Input
                  label=""
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="e.g., gemini-1.5-flash, gpt-4o"
                  required
                />
                <p className="text-gray-500 text-xs mt-1">
                  Common: gemini-1.5-flash, gemini-1.5-pro, gpt-4o, gpt-4o-mini
                </p>
              </div>

              {/* MCP Servers Selection */}
              {mcpServers.length > 0 && (
                <div className="pt-4 border-t border-[#374151]">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="material-symbols-outlined text-gray-400 text-sm">extension</span>
                    <label className="text-sm text-gray-300 font-medium">MCP Servers (Optional)</label>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {mcpServers.map(server => (
                      <button
                        key={server.id}
                        type="button"
                        onClick={() => toggleMcpServer(server.id)}
                        className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                          selectedMcpServerIds.includes(server.id)
                            ? 'bg-[#1173d4] text-white'
                            : 'bg-[#233648] text-gray-300 hover:bg-[#2d4a5f]'
                        }`}
                      >
                        {server.name}
                      </button>
                    ))}
                  </div>
                  <p className="text-gray-500 text-xs mt-2">
                    {selectedMcpServerIds.length} selected
                  </p>
                </div>
              )}

              {/* Internal Tools Selection */}
              {internalTools.length > 0 && (
                <div className="pt-4 border-t border-[#374151]">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="material-symbols-outlined text-gray-400 text-sm">construction</span>
                    <label className="text-sm text-gray-300 font-medium">Internal Tools (Optional)</label>
                  </div>
                  <div className="space-y-3">
                    {internalTools.map(tool => {
                      const isSelected = selectedInternalTools.has(tool.id);
                      const selectedCredId = selectedInternalTools.get(tool.id) || 0;
                      const availableCreds = getCredentialsForTool(tool);

                      return (
                        <div key={tool.id} className="space-y-2">
                          <button
                            type="button"
                            onClick={() => toggleInternalTool(tool.id, tool)}
                            className={`w-full px-3 py-1.5 rounded-md text-sm font-medium transition-colors text-left ${
                              isSelected
                                ? 'bg-[#1173d4] text-white'
                                : 'bg-[#233648] text-gray-300 hover:bg-[#2d4a5f]'
                            }`}
                          >
                            {tool.name}
                          </button>
                          {isSelected && (
                            <div className="pl-2">
                              <Select
                                label=""
                                value={selectedCredId}
                                onChange={(e) => updateInternalToolCredential(tool.id, parseInt(e.target.value))}
                                options={[
                                  { value: 0, label: 'Select credential', disabled: true },
                                  ...availableCreds.map(cred => ({
                                    value: cred.id,
                                    label: `${cred.name} (${cred.credential_type_name})`
                                  }))
                                ]}
                                required
                              />
                              {availableCreds.length === 0 && (
                                <p className="text-yellow-400 text-xs mt-1">
                                  ⚠️ No matching credentials found. Create a {tool.required_credential_type_name} credential.
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-gray-500 text-xs mt-2">
                    {selectedInternalTools.size} selected
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Right: Chat/Test Area */}
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
