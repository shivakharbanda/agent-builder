import React from 'react';
import { Button } from '../ui/Button';

interface SessionControlsProps {
  onNewChat: () => void;
  onStartOver: () => void;
  isConnected: boolean;
  sessionId?: string;
  messageCount: number;
}

export function SessionControls({
  onNewChat,
  onStartOver,
  isConnected,
  sessionId,
  messageCount
}: SessionControlsProps) {
  return (
    <div className="border-b border-[#374151] bg-[#1a2633] px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-400' : 'bg-red-400'
            }`} />
            <span className="text-xs text-gray-400">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {sessionId && (
            <div className="text-xs text-gray-500">
              Session: {sessionId.slice(0, 8)}...
            </div>
          )}

          {messageCount > 0 && (
            <div className="text-xs text-gray-500">
              {messageCount} messages
            </div>
          )}
        </div>

        <div className="flex gap-2">
          {messageCount > 0 && (
            <Button
              size="sm"
              variant="outline"
              onClick={onStartOver}
              leftIcon={<span className="material-symbols-outlined text-sm">refresh</span>}
            >
              Start Over
            </Button>
          )}

          <Button
            size="sm"
            variant="outline"
            onClick={onNewChat}
            leftIcon={<span className="material-symbols-outlined text-sm">add_circle</span>}
          >
            New Chat
          </Button>
        </div>
      </div>
    </div>
  );
}