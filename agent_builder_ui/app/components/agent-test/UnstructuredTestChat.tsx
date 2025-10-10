import React, { useState, useEffect, useRef } from 'react';
import { Button } from '../ui/Button';
import { MarkdownRenderer } from '../ui/MarkdownRenderer';
import type { ConversationMessage } from '../../lib/types';

interface UnstructuredTestChatProps {
  credentialId: number;
  model: string;
  conversationHistory: ConversationMessage[];
  onSendMessage: (message: string) => Promise<void>;
  onClearConversation: () => void;
  testing: boolean;
  error: string | null;
}

export function UnstructuredTestChat({
  credentialId,
  model,
  conversationHistory,
  onSendMessage,
  onClearConversation,
  testing,
  error
}: UnstructuredTestChatProps) {
  const [message, setMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationHistory, testing]);

  // Focus input after sending
  useEffect(() => {
    if (!testing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [testing]);

  const handleSend = async () => {
    if (!message.trim() || testing) return;

    const messageToSend = message;
    setMessage('');

    // Hook handles optimistic update - user message appears immediately
    await onSendMessage(messageToSend);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[500px]">
      {/* Chat Header */}
      <div className="flex items-center justify-between pb-4 border-b border-[#374151]">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-gray-400">chat</span>
          <h3 className="text-white font-medium">Chat with your agent</h3>
        </div>
        {conversationHistory.length > 0 && (
          <Button
            size="sm"
            variant="outline"
            onClick={onClearConversation}
            leftIcon={<span className="material-symbols-outlined text-sm">delete</span>}
          >
            Clear Chat
          </Button>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4 min-h-0">
        {conversationHistory.length === 0 && !testing && (
          <div className="text-center py-12">
            <span className="material-symbols-outlined text-4xl text-gray-500 mb-4 block">
              forum
            </span>
            <h4 className="text-white font-medium mb-2">Start a conversation</h4>
            <p className="text-gray-400 text-sm max-w-md mx-auto">
              Type a message below to start testing your agent. You can have a multi-turn conversation.
            </p>
          </div>
        )}

        {conversationHistory.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-[#1173d4] text-white'
                  : 'bg-[#1a2633] border border-[#374151] text-gray-300'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="material-symbols-outlined text-sm">
                  {msg.role === 'user' ? 'person' : 'smart_toy'}
                </span>
                <span className="text-xs font-medium">
                  {msg.role === 'user' ? 'You' : 'Agent'}
                </span>
              </div>
              <div className="text-sm">
                <MarkdownRenderer content={msg.content} />
              </div>
            </div>
          </div>
        ))}

        {testing && (
          <div className="flex justify-start">
            <div className="bg-[#1a2633] border border-[#374151] rounded-lg px-4 py-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="material-symbols-outlined text-sm text-gray-400">smart_toy</span>
                <span className="text-xs font-medium text-gray-400">Agent</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg mb-3">
          <div className="flex items-start gap-2">
            <span className="material-symbols-outlined text-red-400 text-sm">error</span>
            <p className="text-red-300 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="pt-4 border-t border-[#374151]">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={!credentialId ? "Please select a credential first..." : !model?.trim() ? "Please enter a model name..." : "Type your message..."}
            disabled={testing || !credentialId || !model?.trim()}
            className="flex-1 bg-[#111a22] border border-[#374151] rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#1173d4] focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <Button
            onClick={handleSend}
            disabled={!message.trim() || testing || !credentialId || !model?.trim()}
            loading={testing}
            leftIcon={<span className="material-symbols-outlined text-base">send</span>}
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
