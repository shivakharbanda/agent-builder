import React, { useState, useEffect, useRef } from 'react';
import { ChatMessageComponent, type ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { SessionControls } from './SessionControls';
import { Button } from '../ui/Button';
import { useAgentBuilder } from '../../hooks/useAgentBuilder';
import { checkAgentBuilderHealth } from '../../lib/agentConfigValidator';

interface ChatInterfaceProps {
  onAgentConfigComplete?: (config: any) => void;
  onSwitchToManual?: () => void;
  selectedProject?: number;
}

export function ChatInterface({ onAgentConfigComplete, onSwitchToManual, selectedProject }: ChatInterfaceProps) {
  const { session, createSession, sendMessage, resetSession, checkFinalization } = useAgentBuilder();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [session.messages]);

  // Initialize chat session
  const createNewSession = async () => {
    try {
      await createSession();
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  // Start session on mount with health check
  useEffect(() => {
    const initializeChat = async () => {
      try {
        // Check if FastAPI service is available
        const { AGENT_BUILDER_CONFIG } = await import('../../lib/config');
        const isHealthy = await checkAgentBuilderHealth(AGENT_BUILDER_CONFIG.BASE_URL);

        if (!isHealthy) {
          console.warn('Agent Builder service is not available');
          // Still try to create session - user will see connection errors
        }

        await createNewSession();
      } catch (error) {
        console.error('Failed to initialize chat:', error);
      }
    };

    initializeChat();
  }, []);

  const handleSendMessage = async (message: string) => {
    if (!session.sessionId || session.isLoading) return;

    try {
      await sendMessage(message);

      // Check if configuration is complete
      await checkFinalization();
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const handleStartOver = async () => {
    try {
      await resetSession();
    } catch (error) {
      console.error('Failed to reset session:', error);
    }
  };

  const handleUseConfiguration = () => {
    if (session.finalConfig && onAgentConfigComplete) {
      onAgentConfigComplete(session.finalConfig);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#111a22] rounded-lg border border-[#374151] overflow-hidden">
      {/* Session Controls */}
      <SessionControls
        onNewChat={createNewSession}
        onStartOver={handleStartOver}
        isConnected={session.isConnected}
        sessionId={session.sessionId}
        messageCount={session.messages.length}
      />

      {/* Chat Messages */}
      <div
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0"
      >
        {session.messages.length === 0 && !session.isLoading && (
          <div className="text-center py-8">
            <span className="material-symbols-outlined text-4xl text-gray-500 mb-4 block">smart_toy</span>
            <h3 className="text-lg font-semibold text-white mb-2">AI Agent Builder</h3>
            <p className="text-gray-400 text-sm max-w-md mx-auto mb-4">
              Tell me what kind of agent you want to build, and I'll ask you a few focused questions to create the perfect configuration.
            </p>

            {/* Project Warning */}
            {(!selectedProject || selectedProject === 0) && (
              <div className="max-w-md mx-auto p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <div className="flex items-center gap-2 text-yellow-400 text-sm">
                  <span className="material-symbols-outlined text-sm">warning</span>
                  <span>Please select a project in the Manual Builder tab first</span>
                </div>
              </div>
            )}
          </div>
        )}

        {session.messages.map((message, index) => (
          <ChatMessageComponent key={index} message={message} />
        ))}

        {session.isLoading && (
          <div className="flex justify-start">
            <div className="bg-[#1a2633] border border-[#374151] rounded-lg px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#1173d4] text-sm">smart_toy</span>
                <span className="text-xs text-gray-400">AI Assistant</span>
              </div>
              <div className="flex items-center gap-1 mt-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Completion Actions */}
      {session.isComplete && session.finalConfig && (
        <div className="border-t border-[#374151] bg-[#1a2633] p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-green-400">check_circle</span>
              <span className="text-sm text-white font-medium">Agent configuration complete!</span>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={onSwitchToManual}
              >
                Switch to Manual
              </Button>
              <Button
                size="sm"
                onClick={handleUseConfiguration}
                leftIcon={<span className="material-symbols-outlined text-sm">auto_awesome</span>}
              >
                Use This Configuration
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Chat Input */}
      {!session.isComplete && (
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={session.isLoading || !session.isConnected || !selectedProject || selectedProject === 0}
          placeholder={
            !selectedProject || selectedProject === 0
              ? "Please select a project first..."
              : !session.isConnected
              ? "Connecting..."
              : "Describe the agent you want to build..."
          }
        />
      )}
    </div>
  );
}