import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface ExecutionResultModalProps {
  isOpen: boolean;
  onClose: () => void;
  results: any;
  error?: string | null;
  isExecuting?: boolean;
}

export function ExecutionResultModal({
  isOpen,
  onClose,
  results,
  error,
  isExecuting = false
}: ExecutionResultModalProps) {
  if (!isOpen) return null;

  const formatExecutionTime = (seconds: number) => {
    if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
    if (seconds < 60) return `${seconds.toFixed(2)}s`;
    return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // TODO: Show toast notification
  };

  const downloadAsJson = () => {
    const dataStr = JSON.stringify(results.results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `execution_results_${results.node_id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const renderResultsTable = (data: any[]) => {
    if (!Array.isArray(data) || data.length === 0) {
      return <p className="text-gray-400 text-sm">No results returned</p>;
    }

    const keys = Object.keys(data[0]);

    return (
      <div className="overflow-auto max-h-96">
        <table className="w-full text-sm">
          <thead className="bg-[#0d1829] sticky top-0">
            <tr>
              {keys.map((key) => (
                <th
                  key={key}
                  className="px-4 py-2 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider border-b border-[#374151]"
                >
                  {key}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, index) => (
              <tr
                key={index}
                className="hover:bg-[#1a2633] transition-colors border-b border-[#374151]/50"
              >
                {keys.map((key) => (
                  <td
                    key={key}
                    className="px-4 py-2 text-gray-300"
                  >
                    {typeof row[key] === 'object'
                      ? JSON.stringify(row[key])
                      : String(row[key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderResults = () => {
    if (Array.isArray(results.results)) {
      return renderResultsTable(results.results);
    } else if (typeof results.results === 'object') {
      return (
        <pre className="bg-[#0d1829] p-4 rounded text-sm text-gray-300 overflow-auto max-h-96">
          {JSON.stringify(results.results, null, 2)}
        </pre>
      );
    } else {
      return (
        <pre className="bg-[#0d1829] p-4 rounded text-sm text-gray-300">
          {String(results.results)}
        </pre>
      );
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#374151]">
          <div>
            <h2 className="text-xl font-semibold text-white">
              {isExecuting ? 'Executing Node...' : error ? 'Execution Failed' : 'Execution Results'}
            </h2>
            {results && !error && (
              <p className="text-sm text-gray-400 mt-1">
                Node: {results.node_type} | Time: {formatExecutionTime(results.execution_time)}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
            disabled={isExecuting}
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {/* Loading State */}
          {isExecuting && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#1173d4] mb-4"></div>
              <p className="text-gray-400">Executing node...</p>
            </div>
          )}

          {/* Error State */}
          {error && !isExecuting && (
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
              <div className="flex items-start">
                <span className="material-symbols-outlined text-red-400 mr-3">error</span>
                <div className="flex-1">
                  <h3 className="text-red-400 font-semibold mb-2">Error</h3>
                  <p className="text-gray-300 text-sm">{error}</p>
                  {results?.error_type && (
                    <p className="text-gray-400 text-xs mt-2">Type: {results.error_type}</p>
                  )}
                  {results?.traceback && (
                    <pre className="mt-3 text-xs bg-black/30 p-3 rounded overflow-auto max-h-40 text-gray-400">
                      {results.traceback}
                    </pre>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Success State */}
          {results && !error && !isExecuting && (
            <div className="space-y-4">
              {/* Metadata */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[#1a2633] p-3 rounded-lg">
                  <p className="text-xs text-gray-400 mb-1">Status</p>
                  <p className="text-green-400 font-semibold flex items-center">
                    <span className="material-symbols-outlined text-sm mr-1">check_circle</span>
                    {results.status}
                  </p>
                </div>
                <div className="bg-[#1a2633] p-3 rounded-lg">
                  <p className="text-xs text-gray-400 mb-1">Node Type</p>
                  <p className="text-white font-semibold">{results.node_type}</p>
                </div>
                <div className="bg-[#1a2633] p-3 rounded-lg">
                  <p className="text-xs text-gray-400 mb-1">Execution Time</p>
                  <p className="text-white font-semibold">{formatExecutionTime(results.execution_time)}</p>
                </div>
                <div className="bg-[#1a2633] p-3 rounded-lg">
                  <p className="text-xs text-gray-400 mb-1">Rows Returned</p>
                  <p className="text-white font-semibold">
                    {Array.isArray(results.results) ? results.results.length : 'N/A'}
                  </p>
                </div>
              </div>

              {/* Results */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-white font-semibold">Results</h3>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => copyToClipboard(JSON.stringify(results.results, null, 2))}
                      className="text-gray-400 hover:text-white text-xs flex items-center transition-colors"
                    >
                      <span className="material-symbols-outlined text-sm mr-1">content_copy</span>
                      Copy
                    </button>
                    <button
                      onClick={downloadAsJson}
                      className="text-gray-400 hover:text-white text-xs flex items-center transition-colors"
                    >
                      <span className="material-symbols-outlined text-sm mr-1">download</span>
                      Download
                    </button>
                  </div>
                </div>
                <div className="bg-[#0d1829] rounded-lg p-4">
                  {renderResults()}
                </div>
              </div>

              {/* Metadata Details */}
              {results.metadata && Object.keys(results.metadata).length > 0 && (
                <div>
                  <h3 className="text-white font-semibold mb-3">Execution Metadata</h3>
                  <div className="bg-[#0d1829] rounded-lg p-4">
                    <pre className="text-xs text-gray-400 overflow-auto">
                      {JSON.stringify(results.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end p-6 border-t border-[#374151] space-x-3">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isExecuting}
          >
            Close
          </Button>
        </div>
      </Card>
    </div>
  );
}
