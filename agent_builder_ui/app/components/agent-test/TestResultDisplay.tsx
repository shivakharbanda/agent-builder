import React, { useState } from 'react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface TestResultDisplayProps {
  success: boolean;
  output?: Record<string, any>;  // For structured results
  response?: string;  // For unstructured results
  executionTimeMs: number;
  error?: string;
  mode: 'structured' | 'unstructured';
}

export function TestResultDisplay({
  success,
  output,
  response,
  executionTimeMs,
  error,
  mode
}: TestResultDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const textToCopy = mode === 'structured'
      ? JSON.stringify(output, null, 2)
      : response || '';

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!success && error) {
    return (
      <Card variant="border" className="p-4 bg-red-500/10 border-red-500/20">
        <div className="flex items-start gap-3">
          <span className="material-symbols-outlined text-red-400 text-xl">error</span>
          <div className="flex-1">
            <h4 className="text-red-400 font-medium mb-1">Execution Failed</h4>
            <p className="text-red-300 text-sm">{error}</p>
            <p className="text-red-400/70 text-xs mt-2">
              Time: {executionTimeMs}ms
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card variant="border" className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-green-400">check_circle</span>
          <h4 className="text-white font-medium">Test Result</h4>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">
            {executionTimeMs}ms
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopy}
            leftIcon={
              <span className="material-symbols-outlined text-sm">
                {copied ? 'check' : 'content_copy'}
              </span>
            }
          >
            {copied ? 'Copied!' : 'Copy'}
          </Button>
        </div>
      </div>

      {mode === 'structured' && output ? (
        <div className="bg-[#111a22] rounded-md p-4 overflow-auto max-h-96">
          <pre className="text-sm text-gray-300">
            {JSON.stringify(output, null, 2)}
          </pre>
        </div>
      ) : mode === 'unstructured' && response ? (
        <div className="bg-[#111a22] rounded-md p-4">
          <p className="text-gray-300 text-sm whitespace-pre-wrap">{response}</p>
        </div>
      ) : null}
    </Card>
  );
}
