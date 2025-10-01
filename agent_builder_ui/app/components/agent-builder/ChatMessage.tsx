import React from 'react';

export interface ChatMessage {
  role: 'user' | 'model';
  content: string;
  timestamp: string;
}

interface ChatMessageProps {
  message: ChatMessage;
}

export function ChatMessageComponent({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] rounded-lg px-4 py-3 ${
        isUser
          ? 'bg-[#1173d4] text-white ml-auto'
          : 'bg-[#1a2633] text-gray-100 border border-[#374151]'
      }`}>
        {!isUser && (
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-[#1173d4] text-sm">smart_toy</span>
            <span className="text-xs text-gray-400 font-medium">AI Assistant</span>
          </div>
        )}

        <div className="text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>

        <div className={`text-xs mt-2 ${
          isUser ? 'text-blue-100' : 'text-gray-500'
        }`}>
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      </div>
    </div>
  );
}