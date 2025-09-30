import { useState, useEffect } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import nodeConfigs from './config/nodeConfigs.json';
import { useCredentials, useAgents } from '../../hooks/useAPI';
import { APP_CONFIG } from '../../lib/config';

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

  // Get node configuration from JSON
  const nodeConfig: NodeConfig = (nodeConfigs as any)[nodeType];

  // API hooks for fetching data
  const { data: credentials, loading: credentialsLoading, error: credentialsError } = useCredentials();
  const { data: agents, loading: agentsLoading, error: agentsError } = useAgents();

  useEffect(() => {
    if (isOpen && nodeData?.config) {
      setConfig(nodeData.config);
    } else if (isOpen) {
      // Initialize with default values
      const defaultConfig: any = {};
      nodeConfig?.fields?.forEach(field => {
        if (field.default !== undefined) {
          defaultConfig[field.name] = field.default;
        }
      });
      setConfig(defaultConfig);
    }
  }, [isOpen, nodeData, nodeConfig]);

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