import React, { useState, useEffect } from 'react';
import { Button } from '../ui/Button';
import { Input, Textarea } from '../ui/Input';
import { TestResultDisplay } from './TestResultDisplay';

interface StructuredTestFormProps {
  placeholders: string[];
  credentialId: number;
  model: string;
  onRun: (inputs: Record<string, any>) => Promise<void>;
  testing: boolean;
  testResult: any;
  error: string | null;
}

export function StructuredTestForm({
  placeholders,
  credentialId,
  model,
  onRun,
  testing,
  testResult,
  error
}: StructuredTestFormProps) {
  const [inputs, setInputs] = useState<Record<string, string>>({});

  // Initialize inputs
  useEffect(() => {
    const initialInputs: Record<string, string> = {};
    placeholders.forEach(placeholder => {
      initialInputs[placeholder] = '';
    });
    setInputs(initialInputs);
  }, [placeholders]);

  const handleInputChange = (placeholder: string, value: string) => {
    setInputs(prev => ({
      ...prev,
      [placeholder]: value
    }));
  };

  const handleRun = () => {
    // Convert empty strings to meaningful values if needed
    const processedInputs = { ...inputs };
    onRun(processedInputs);
  };

  const isValid = (placeholders.length === 0 || placeholders.every(p => inputs[p]?.trim())) && model?.trim();

  return (
    <div className="space-y-6">
      {/* Input Form */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-4">
          <span className="material-symbols-outlined text-gray-400">edit_note</span>
          <h3 className="text-white font-medium">Fill in the required inputs:</h3>
        </div>

        {placeholders.length === 0 ? (
          <div className="text-center py-8 bg-[#111a22] rounded-lg border border-[#374151]">
            <span className="material-symbols-outlined text-gray-500 text-3xl mb-2">info</span>
            <p className="text-gray-400 text-sm">
              This agent has no placeholders. Click "Run Agent" to execute with default prompts.
            </p>
          </div>
        ) : (
          <>
            {placeholders.map((placeholder, index) => {
              // Determine if this should be a textarea (for longer text)
              const isTextArea = placeholder.toLowerCase().includes('text') ||
                                 placeholder.toLowerCase().includes('message') ||
                                 placeholder.toLowerCase().includes('content') ||
                                 placeholder.toLowerCase().includes('description');

              return (
                <div key={placeholder}>
                  {isTextArea ? (
                    <Textarea
                      label={placeholder.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      placeholder={`Enter ${placeholder.replace(/_/g, ' ')}...`}
                      value={inputs[placeholder] || ''}
                      onChange={(e) => handleInputChange(placeholder, e.target.value)}
                      required
                      className="min-h-[100px]"
                      autoFocus={index === 0}
                    />
                  ) : (
                    <Input
                      label={placeholder.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      placeholder={`Enter ${placeholder.replace(/_/g, ' ')}...`}
                      value={inputs[placeholder] || ''}
                      onChange={(e) => handleInputChange(placeholder, e.target.value)}
                      required
                      autoFocus={index === 0}
                    />
                  )}
                </div>
              );
            })}
          </>
        )}
      </div>

      {/* Run Button */}
      <div className="flex justify-end">
        <Button
          onClick={handleRun}
          disabled={!isValid || testing || !credentialId}
          loading={testing}
          leftIcon={<span className="material-symbols-outlined text-base">play_arrow</span>}
        >
          {testing ? 'Running...' : 'Run Agent'}
        </Button>
      </div>

      {/* Error Display */}
      {error && !testResult && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <div className="flex items-start gap-2">
            <span className="material-symbols-outlined text-red-400 text-sm">error</span>
            <p className="text-red-300 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Test Result */}
      {testResult && (
        <TestResultDisplay
          success={testResult.success}
          output={testResult.output}
          executionTimeMs={testResult.execution_time_ms}
          error={testResult.error}
          mode="structured"
        />
      )}
    </div>
  );
}
