import React, { useState, useEffect } from 'react';
import { Button } from '../ui/Button';

interface WorkflowProperties {
  watermark_start_date?: string;
  watermark_end_date?: string;
  schedule?: string;
  timeout?: number;
  retry_count?: number;
  notification_email?: string;
}

interface WorkflowPropertiesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (properties: WorkflowProperties) => void;
  initialProperties: WorkflowProperties;
}

export function WorkflowPropertiesModal({
  isOpen,
  onClose,
  onSave,
  initialProperties
}: WorkflowPropertiesModalProps) {
  const [properties, setProperties] = useState<WorkflowProperties>(initialProperties);

  useEffect(() => {
    setProperties(initialProperties);
  }, [initialProperties, isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(properties);
    onClose();
  };

  const handleInputChange = (field: keyof WorkflowProperties, value: string | number) => {
    setProperties(prev => ({
      ...prev,
      [field]: value || undefined
    }));
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-[#1a2633] border border-[#374151] rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-[#374151]">
            <h2 className="text-lg font-semibold text-white">Workflow Properties</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
              type="button"
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          {/* Body */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-8rem)]">
            <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-4">
          {/* Watermark Dates */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Watermark Start Date
              </label>
              <input
                type="datetime-local"
                value={properties.watermark_start_date || ''}
                onChange={(e) => handleInputChange('watermark_start_date', e.target.value)}
                className="w-full px-3 py-2 bg-[#1f2937] border border-[#374151] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#1173d4] focus:border-transparent"
                placeholder="Select start date"
              />
              <p className="text-xs text-gray-500 mt-1">
                Start date for data processing watermark
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Watermark End Date
              </label>
              <input
                type="datetime-local"
                value={properties.watermark_end_date || ''}
                onChange={(e) => handleInputChange('watermark_end_date', e.target.value)}
                className="w-full px-3 py-2 bg-[#1f2937] border border-[#374151] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#1173d4] focus:border-transparent"
                placeholder="Select end date"
              />
              <p className="text-xs text-gray-500 mt-1">
                End date for data processing watermark
              </p>
            </div>
          </div>

          {/* Schedule */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Schedule (Cron Expression)
            </label>
            <input
              type="text"
              value={properties.schedule || ''}
              onChange={(e) => handleInputChange('schedule', e.target.value)}
              className="w-full px-3 py-2 bg-[#1f2937] border border-[#374151] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#1173d4] focus:border-transparent"
              placeholder="0 0 * * * (daily at midnight)"
            />
            <p className="text-xs text-gray-500 mt-1">
              Cron expression for workflow scheduling
            </p>
          </div>

          {/* Timeout and Retry */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Timeout (seconds)
              </label>
              <input
                type="number"
                min="0"
                value={properties.timeout || ''}
                onChange={(e) => handleInputChange('timeout', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-[#1f2937] border border-[#374151] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#1173d4] focus:border-transparent"
                placeholder="3600"
              />
              <p className="text-xs text-gray-500 mt-1">
                Maximum execution time in seconds
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Retry Count
              </label>
              <input
                type="number"
                min="0"
                max="10"
                value={properties.retry_count || ''}
                onChange={(e) => handleInputChange('retry_count', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-[#1f2937] border border-[#374151] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#1173d4] focus:border-transparent"
                placeholder="3"
              />
              <p className="text-xs text-gray-500 mt-1">
                Number of retry attempts on failure
              </p>
            </div>
          </div>

          {/* Notification Email */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Notification Email
            </label>
            <input
              type="email"
              value={properties.notification_email || ''}
              onChange={(e) => handleInputChange('notification_email', e.target.value)}
              className="w-full px-3 py-2 bg-[#1f2937] border border-[#374151] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#1173d4] focus:border-transparent"
              placeholder="user@example.com"
            />
            <p className="text-xs text-gray-500 mt-1">
              Email address for workflow notifications
            </p>
          </div>
        </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-[#374151]">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancel
                </Button>
                <Button type="submit">
                  Save Properties
                </Button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}