import { useState } from 'react';
import type { WorkflowConfig } from './types';

interface ConfigViewerProps {
  config: WorkflowConfig;
  isVisible: boolean;
  onToggle: () => void;
}

export function ConfigViewer({ config, isVisible, onToggle }: ConfigViewerProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'json'>('json');

  const formatConfig = () => {
    return JSON.stringify(config, null, 2);
  };

  const getConfigStats = () => {
    return {
      nodeCount: config.nodes.length,
      edgeCount: config.edges.length,
      configuredNodes: config.nodes.filter(node =>
        Object.keys(node.config).some(key => node.config[key])
      ).length,
      lastUpdated: new Date(config.metadata.updated).toISOString().replace('T', ' ').slice(0, 19)
    };
  };

  const stats = getConfigStats();

  return (
    <>
      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className="fixed top-4 right-4 z-20 bg-[#1a2633] border border-[#374151] rounded-lg p-3 text-white hover:bg-[#233648] transition-colors shadow-lg"
        title="View Workflow Configuration"
      >
        <div className="flex items-center space-x-2">
          <span className="material-symbols-outlined text-lg">code</span>
          <span className="text-sm font-medium">JSON</span>
          {stats.nodeCount > 0 && (
            <span className="bg-[#1173d4] text-xs px-2 py-1 rounded-full">
              {stats.nodeCount}
            </span>
          )}
        </div>
      </button>

      {/* Config Panel */}
      {isVisible && (
        <div className="fixed inset-y-0 right-0 w-96 bg-[#1a2633] border-l border-[#374151] z-30 flex flex-col shadow-2xl">
          {/* Header */}
          <div className="p-4 border-b border-[#374151]">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-white">Workflow Data</h3>
              <button
                onClick={onToggle}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {/* Tabs */}
            <div className="flex space-x-1">
              <button
                onClick={() => setActiveTab('json')}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  activeTab === 'json'
                    ? 'bg-[#1173d4] text-white'
                    : 'bg-[#111a22] text-gray-400 hover:text-white'
                }`}
              >
                JSON
              </button>
              <button
                onClick={() => setActiveTab('overview')}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  activeTab === 'overview'
                    ? 'bg-[#1173d4] text-white'
                    : 'bg-[#111a22] text-gray-400 hover:text-white'
                }`}
              >
                Overview
              </button>
            </div>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-hidden">
            {activeTab === 'json' ? (
              /* JSON View */
              <div className="h-full p-4 flex flex-col">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold text-white">Workflow JSON</h4>
                  <button
                    onClick={() => navigator.clipboard.writeText(formatConfig())}
                    className="px-3 py-1 text-xs bg-[#1173d4] text-white rounded hover:bg-[#0f5aa3] transition-colors"
                    title="Copy JSON to clipboard"
                  >
                    📋 Copy
                  </button>
                </div>
                <div className="flex-1 bg-[#111a22] border border-[#374151] rounded p-3 overflow-auto">
                  <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono">
                    {formatConfig()}
                  </pre>
                </div>
              </div>
            ) : (
              /* Overview Tab */
              <div className="h-full overflow-y-auto">
                {/* Stats */}
                <div className="p-4 border-b border-[#374151]">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-[#1173d4]">{stats.nodeCount}</div>
                      <div className="text-xs text-gray-400">Nodes</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-[#1173d4]">{stats.edgeCount}</div>
                      <div className="text-xs text-gray-400">Connections</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-400">{stats.configuredNodes}</div>
                      <div className="text-xs text-gray-400">Configured</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xs font-bold text-gray-300">{config.metadata.version}</div>
                      <div className="text-xs text-gray-400">Version</div>
                    </div>
                  </div>
                  <div className="mt-3 text-xs text-gray-400">
                    Last updated: {stats.lastUpdated}
                  </div>
                </div>

                {/* Workflow Info */}
                <div className="p-4 border-b border-[#374151]">
                  <h4 className="text-sm font-semibold text-white mb-2">Workflow Info</h4>
                  <div className="space-y-2">
                    <div>
                      <span className="text-xs text-gray-400">Name:</span>
                      <div className="text-sm text-white">{config.metadata.name}</div>
                    </div>
                    {config.metadata.description && (
                      <div>
                        <span className="text-xs text-gray-400">Description:</span>
                        <div className="text-sm text-white">{config.metadata.description}</div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Workflow Properties */}
                <div className="p-4 border-b border-[#374151]">
                  <h4 className="text-sm font-semibold text-white mb-2">Properties</h4>
                  <div className="space-y-2">
                    <div className="grid grid-cols-1 gap-2">
                      {config.properties.watermark_start_date && (
                        <div>
                          <span className="text-xs text-gray-400">Watermark Start:</span>
                          <div className="text-sm text-white">
                            {new Date(config.properties.watermark_start_date).toISOString().replace('T', ' ').slice(0, 19)}
                          </div>
                        </div>
                      )}
                      {config.properties.watermark_end_date && (
                        <div>
                          <span className="text-xs text-gray-400">Watermark End:</span>
                          <div className="text-sm text-white">
                            {new Date(config.properties.watermark_end_date).toISOString().replace('T', ' ').slice(0, 19)}
                          </div>
                        </div>
                      )}
                      {config.properties.schedule && (
                        <div>
                          <span className="text-xs text-gray-400">Schedule:</span>
                          <div className="text-sm text-white font-mono">{config.properties.schedule}</div>
                        </div>
                      )}
                      {config.properties.timeout && (
                        <div>
                          <span className="text-xs text-gray-400">Timeout:</span>
                          <div className="text-sm text-white">{config.properties.timeout}s</div>
                        </div>
                      )}
                      {config.properties.retry_count !== undefined && (
                        <div>
                          <span className="text-xs text-gray-400">Retry Count:</span>
                          <div className="text-sm text-white">{config.properties.retry_count}</div>
                        </div>
                      )}
                      {config.properties.notification_email && (
                        <div>
                          <span className="text-xs text-gray-400">Notification Email:</span>
                          <div className="text-sm text-white">{config.properties.notification_email}</div>
                        </div>
                      )}
                      {!config.properties.watermark_start_date &&
                       !config.properties.watermark_end_date &&
                       !config.properties.schedule &&
                       !config.properties.timeout &&
                       !config.properties.notification_email && (
                        <div className="text-sm text-gray-400 italic">No properties configured</div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Node Breakdown */}
                {config.nodes.length > 0 && (
                  <div className="p-4">
                    <h4 className="text-sm font-semibold text-white mb-2">Nodes</h4>
                    <div className="space-y-2">
                      {config.nodes.map((node) => (
                        <div key={node.id} className="flex items-center justify-between p-2 bg-[#111a22] rounded">
                          <div className="flex items-center space-x-2">
                            <span className="material-symbols-outlined text-[#1173d4] text-sm">
                              {node.type === 'database' ? 'storage' :
                               node.type === 'agent' ? 'smart_toy' :
                               node.type === 'output' ? 'output' : 'code'}
                            </span>
                            <span className="text-xs text-white truncate">{node.id}</span>
                          </div>
                          <div className={`w-2 h-2 rounded-full ${
                            Object.keys(node.config).some(key => node.config[key])
                              ? 'bg-green-400'
                              : 'bg-gray-400'
                          }`}></div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Overlay */}
      {isVisible && (
        <div
          className="fixed inset-0 bg-black/20 z-20"
          onClick={onToggle}
        />
      )}
    </>
  );
}