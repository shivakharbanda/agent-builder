import React from 'react';

interface ProgressStep {
  key: string;
  label: string;
  completed: boolean;
}

interface ProgressIndicatorProps {
  steps: ProgressStep[];
  currentStep?: string;
}

export function ProgressIndicator({ steps, currentStep }: ProgressIndicatorProps) {
  const completedCount = steps.filter(step => step.completed).length;
  const progressPercentage = (completedCount / steps.length) * 100;

  return (
    <div className="border-b border-[#374151] bg-[#111a22] px-4 py-3">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-white">Agent Configuration Progress</h3>
        <span className="text-xs text-gray-400">
          {completedCount} of {steps.length} steps
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-[#374151] rounded-full h-2 mb-3">
        <div
          className="bg-[#1173d4] h-2 rounded-full transition-all duration-300"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      {/* Step Indicators */}
      <div className="flex items-center gap-4 overflow-x-auto">
        {steps.map((step, index) => (
          <div
            key={step.key}
            className={`flex items-center gap-2 text-xs whitespace-nowrap ${
              step.completed
                ? 'text-green-400'
                : step.key === currentStep
                ? 'text-[#1173d4]'
                : 'text-gray-500'
            }`}
          >
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
              step.completed
                ? 'bg-green-400 text-white'
                : step.key === currentStep
                ? 'bg-[#1173d4] text-white'
                : 'bg-[#374151] text-gray-400'
            }`}>
              {step.completed ? (
                <span className="material-symbols-outlined text-sm">check</span>
              ) : (
                index + 1
              )}
            </div>
            <span className="hidden sm:inline">{step.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Predefined steps for agent building
export const AGENT_BUILDING_STEPS: ProgressStep[] = [
  { key: 'type', label: 'Agent Type', completed: false },
  { key: 'name', label: 'Name', completed: false },
  { key: 'description', label: 'Description', completed: false },
  { key: 'system_prompt', label: 'System Prompt', completed: false },
  { key: 'user_prompt', label: 'User Prompt', completed: false },
  { key: 'schema', label: 'Output Schema', completed: false },
];