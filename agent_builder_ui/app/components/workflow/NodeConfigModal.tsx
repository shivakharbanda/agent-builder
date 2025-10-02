import { useState, useEffect } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import nodeConfigs from './config/nodeConfigs.json';
import { useCredentials, useAgents } from '../../hooks/useAPI';
import { APP_CONFIG } from '../../lib/config';
import { api } from '../../lib/api';

interface NodeConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  nodeType: string;
  nodeData: any;
  onSave: (config: any) => void;
}

interface NodeConfig {
  name: string;
  description: string;
  icon: string;
  category: string;
  fields: any[];
  inputs?: any[];
  outputs?: any[];
}

export function NodeConfigModal({ isOpen, onClose, nodeType, nodeData, onSave }: NodeConfigModalProps) {
  const [config, setConfig] = useState<any>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  // Schema inspection state
  const [schemaData, setSchemaData] = useState<any>(null);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  // Get node configuration from JSON
  const nodeConfig: NodeConfig = (nodeConfigs as any)[nodeType];

  // API hooks for fetching data
  const { data: credentials, loading: credentialsLoading, error: credentialsError } = useCredentials();
  const { data: agents, loading: agentsLoading, error: agentsError } = useAgents();

  useEffect(() => {
    // Debug logging
    if (isOpen) {
      console.log('[NodeConfigModal] Opening modal:', {
        nodeType,
        nodeData,
        hasConfig: !!nodeData?.config,
        configKeys: nodeData?.config ? Object.keys(nodeData.config) : [],
        config: nodeData?.config
      });
    }

    if (isOpen) {
      // Check if we have existing config with actual values (not just 'label')
      const hasExistingConfig = nodeData?.config &&
        Object.keys(nodeData.config).length > 0 &&
        Object.keys(nodeData.config).some(key => key !== 'label' && nodeData.config[key]);

      if (hasExistingConfig) {
        // Has existing config - use it
        console.log('[NodeConfigModal] Loading existing config:', nodeData.config);
        setConfig(nodeData.config);
      } else {
        // No config or only has label - initialize with defaults
        console.log('[NodeConfigModal] Initializing with defaults');
        const defaultConfig: any = {};
        nodeConfig?.fields?.forEach(field => {
          if (field.default !== undefined) {
            defaultConfig[field.name] = field.default;
          }
        });
        // If there's a label, preserve it
        if (nodeData?.config?.label) {
          defaultConfig.label = nodeData.config.label;
        }
        setConfig(defaultConfig);
      }
    }
  }, [isOpen, nodeData, nodeType, nodeConfig]);

  const handleFieldChange = (fieldName: string, value: any) => {
    setConfig((prev: any) => ({
      ...prev,
      [fieldName]: value
    }));

    // Clear error when user starts typing
    if (errors[fieldName]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[fieldName];
        return newErrors;
      });
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};


    nodeConfig?.fields?.forEach(field => {
      // Check required fields (only for non-conditional fields)
      if (field.required && !field.conditional && (!config[field.name] || config[field.name] === '')) {
        newErrors[field.name] = `${field.label} is required`;
      }

      // Check conditional required fields
      if (field.conditional && shouldShowField(field)) {
        if (field.required && (!config[field.name] || config[field.name] === '')) {
          newErrors[field.name] = `${field.label} is required`;
        }
      }

      // Type-specific validation
      if (config[field.name]) {
        switch (field.type) {
          case 'number':
            const num = Number(config[field.name]);
            if (isNaN(num)) {
              newErrors[field.name] = `${field.label} must be a valid number`;
            } else {
              if (field.min !== undefined && num < field.min) {
                newErrors[field.name] = `${field.label} must be at least ${field.min}`;
              }
              if (field.max !== undefined && num > field.max) {
                newErrors[field.name] = `${field.label} must be at most ${field.max}`;
              }
            }
            break;
        }
      }
    });


    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      await onSave(config);
      onClose();
    } catch (error) {
    } finally {
      setLoading(false);
    }
  };

  const handleInspectSchema = async () => {
    const credentialId = config.credential_id;
    if (!credentialId) {
      setSchemaError('Please select a database credential first');
      return;
    }

    setSchemaLoading(true);
    setSchemaError(null);

    try {
      const schema = await api.inspectDatabaseSchema(Number(credentialId));
      setSchemaData(schema);
    } catch (error: any) {
      setSchemaError(error.response?.data?.error || error.message || 'Failed to inspect schema');
    } finally {
      setSchemaLoading(false);
    }
  };

  const toggleTableExpansion = (tableName: string) => {
    setExpandedTables(prev => {
      const newSet = new Set(prev);
      if (newSet.has(tableName)) {
        newSet.delete(tableName);
      } else {
        newSet.add(tableName);
      }
      return newSet;
    });
  };

  const shouldShowField = (field: any) => {
    if (!field.conditional) return true;

    const conditionValue = config[field.conditional.field];
    return conditionValue === field.conditional.value;
  };

  const renderField = (field: any) => {
    const fieldError = errors[field.name];
    const fieldValue = config[field.name] || '';

    // Don't render if conditional field is hidden
    if (!shouldShowField(field)) {
      return null;
    }

    switch (field.type) {
      case 'text':
      case 'textarea':
        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            {field.type === 'textarea' ? (
              <textarea
                value={fieldValue}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
                placeholder={field.placeholder}
                rows={field.rows || 3}
                className={`w-full bg-[#111a22] border rounded-md px-3 py-2 text-white text-sm resize-none ${
                  fieldError ? 'border-red-500' : 'border-[#374151] focus:border-[#1173d4]'
                }`}
              />
            ) : (
              <Input
                type="text"
                value={fieldValue}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
                placeholder={field.placeholder}
                className={fieldError ? 'border-red-500' : ''}
              />
            )}
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
          </div>
        );

      case 'number':
        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            <Input
              type="number"
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              placeholder={field.placeholder}
              min={field.min}
              max={field.max}
              className={fieldError ? 'border-red-500' : ''}
            />
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
          </div>
        );

      case 'select':
        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            <select
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              className={`w-full bg-[#111a22] border rounded-md px-3 py-2 text-white text-sm ${
                fieldError ? 'border-red-500' : 'border-[#374151] focus:border-[#1173d4]'
              }`}
            >
              <option value="">{field.placeholder || 'Select an option'}</option>
              {field.options?.map((option: any) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
          </div>
        );

      case 'credential_select':
        // Filter credentials by category if specified
        const filteredCredentials = credentials?.results?.filter((cred: any) => {
          if (!field.category_filter) return true;
          // Check both possible field names for category
          return cred.credential_type?.category?.name === field.category_filter ||
                 cred.credential_type_category === field.category_filter ||
                 (cred.credential_type && cred.credential_type.includes(field.category_filter));
        }) || [];

        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            <select
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              disabled={credentialsLoading}
              className={`w-full bg-[#111a22] border rounded-md px-3 py-2 text-white text-sm ${
                fieldError ? 'border-red-500' : 'border-[#374151] focus:border-[#1173d4]'
              } ${credentialsLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <option value="">
                {credentialsLoading ? 'Loading credentials...' : (field.placeholder || 'Select a credential')}
              </option>
              {credentialsError ? (
                <option disabled>Error loading credentials</option>
              ) : credentials?.results?.length === 0 ? (
                <option disabled>No credentials found</option>
              ) : filteredCredentials.length === 0 && field.category_filter ? (
                <option disabled>No {field.category_filter} credentials found</option>
              ) : (
                filteredCredentials.map((credential: any) => (
                  <option key={credential.id} value={credential.id}>
                    {credential.name} ({credential.credential_type?.type_name || credential.credential_type_name || 'Unknown Type'})
                  </option>
                ))
              )}
            </select>
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {/* Debug info */}
            {APP_CONFIG.ENABLE_DEBUG && (
              <div className="text-xs text-gray-500 mt-1">
                Total credentials: {credentials?.results?.length || 0},
                Filtered: {filteredCredentials.length}
                {field.category_filter && ` (filter: ${field.category_filter})`}
              </div>
            )}

            {/* Schema Inspector for Database Nodes */}
            {nodeType === 'database' && field.name === 'credential_id' && (
              <div className="mt-2">
                <button
                  type="button"
                  onClick={handleInspectSchema}
                  disabled={!fieldValue || schemaLoading}
                  className="text-sm px-3 py-1.5 bg-[#1173d4] hover:bg-[#0d5aa7] disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded flex items-center gap-1 transition-colors"
                >
                  <span className="material-symbols-outlined text-sm">
                    {schemaLoading ? 'progress_activity' : 'schema'}
                  </span>
                  {schemaLoading ? 'Loading Schema...' : 'View Schema'}
                </button>

                {schemaError && (
                  <div className="mt-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded p-2">
                    {schemaError}
                  </div>
                )}

                {schemaData && (
                  <div className="mt-3 bg-[#0a1219] border border-[#374151] rounded-lg p-3 max-h-96 overflow-y-auto">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-white flex items-center gap-2">
                        <span className="material-symbols-outlined text-base">database</span>
                        {schemaData.metadata?.data_source_id || 'Unknown'} ({schemaData.database_type})
                      </h4>
                      <span className="text-xs text-gray-400">{schemaData.metadata?.tables?.length || 0} tables</span>
                    </div>

                    <div className="space-y-2">
                      {schemaData.metadata?.tables?.map((table: any) => {
                        const tableName = table.table_name;
                        const isExpanded = expandedTables.has(tableName);

                        return (
                          <div key={tableName} className="border border-[#374151] rounded">
                            <button
                              type="button"
                              onClick={() => toggleTableExpansion(tableName)}
                              className="w-full px-3 py-2 flex items-center justify-between hover:bg-[#111a22] transition-colors"
                            >
                              <span className="flex items-center gap-2 text-sm text-white">
                                <span className="material-symbols-outlined text-sm">
                                  {isExpanded ? 'expand_more' : 'chevron_right'}
                                </span>
                                <span className="material-symbols-outlined text-sm">table</span>
                                {tableName}
                              </span>
                              <span className="text-xs text-gray-400">
                                {table.columns?.length || 0} columns
                              </span>
                            </button>

                            {isExpanded && (
                              <div className="px-3 pb-3 pt-1 space-y-2">
                                <div>
                                  <p className="text-xs text-gray-400 mb-1">Columns:</p>
                                  <div className="space-y-1">
                                    {table.columns?.map((col: any, idx: number) => (
                                      <div
                                        key={idx}
                                        className="flex items-center gap-2 text-xs bg-[#111a22] rounded px-2 py-1"
                                      >
                                        <span className="material-symbols-outlined text-xs text-gray-400">
                                          {col.is_nullable === 'YES' ? 'toggle_off' : 'toggle_on'}
                                        </span>
                                        <span className="text-white font-mono">{col.column_name}</span>
                                        <span className="text-gray-400">({col.data_type})</span>
                                        {col.is_nullable === 'NO' && (
                                          <span className="text-red-400 text-[10px]">NOT NULL</span>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>

                                {table.sample_data && table.sample_data.length > 0 && (
                                  <div>
                                    <p className="text-xs text-gray-400 mb-1">Sample Data:</p>
                                    <div className="text-xs bg-[#111a22] rounded p-2 overflow-x-auto">
                                      <pre className="text-gray-300 font-mono">
                                        {JSON.stringify(table.sample_data, null, 2)}
                                      </pre>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );

      case 'agent_select':
        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            <select
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              disabled={agentsLoading}
              className={`w-full bg-[#111a22] border rounded-md px-3 py-2 text-white text-sm ${
                fieldError ? 'border-red-500' : 'border-[#374151] focus:border-[#1173d4]'
              } ${agentsLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <option value="">
                {agentsLoading ? 'Loading agents...' : (field.placeholder || 'Select an agent')}
              </option>
              {agentsError ? (
                <option disabled>Error loading agents</option>
              ) : agents?.results?.length === 0 ? (
                <option disabled>No agents found</option>
              ) : (
                agents?.results?.map((agent: any) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name} ({agent.return_type})
                  </option>
                ))
              )}
            </select>
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {/* Debug info */}
            {APP_CONFIG.ENABLE_DEBUG && (
              <div className="text-xs text-gray-500 mt-1">
                Total agents: {agents?.results?.length || 0}
              </div>
            )}
          </div>
        );

      case 'code_editor':
        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            <textarea
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              placeholder={field.placeholder}
              rows={field.rows || 8}
              className={`w-full bg-[#111a22] border rounded-md px-3 py-2 text-white text-sm font-mono resize-none ${
                fieldError ? 'border-red-500' : 'border-[#374151] focus:border-[#1173d4]'
              }`}
              style={{ fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace' }}
            />
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
          </div>
        );

      default:
        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label} (Unsupported field type: {field.type})
            </label>
            <Input
              type="text"
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              placeholder={field.placeholder}
              disabled
            />
          </div>
        );
    }
  };

  if (!isOpen || !nodeConfig) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-[#1a2633] rounded-lg border border-[#374151] w-full max-w-2xl max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-[#374151]">
            <div className="flex items-center space-x-3">
              <span className="material-symbols-outlined text-[#1173d4] text-2xl">
                {nodeConfig.icon}
              </span>
              <div>
                <h2 className="text-xl font-semibold text-white">
                  Configure {nodeConfig.name}
                </h2>
                <p className="text-gray-400 text-sm mt-1">
                  {nodeConfig.description}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          {/* API Errors */}
          {(credentialsError || agentsError) && (
            <div className="px-6 pt-4">
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                <div className="text-red-400 text-sm">
                  <span className="material-symbols-outlined text-sm mr-2">warning</span>
                  {credentialsError && `Credentials: ${credentialsError}`}
                  {credentialsError && agentsError && ' | '}
                  {agentsError && `Agents: ${agentsError}`}
                </div>
              </div>
            </div>
          )}

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[60vh]">
            {nodeConfig.fields?.map(renderField)}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end space-x-3 p-6 border-t border-[#374151]">
            <Button
              variant="outline"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined text-sm mr-1 animate-spin">
                    progress_activity
                  </span>
                  Saving...
                </>
              ) : (
                'Save Configuration'
              )}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}