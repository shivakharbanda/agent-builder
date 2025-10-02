import { useState, useEffect, useRef } from 'react';
import { Input } from '../ui/Input';
import { useWorkflowBuilder } from '../../hooks/useWorkflowBuilder';
import { checkWorkflowBuilderHealth } from '../../lib/workflowConfigValidator';

interface ChatMessage {
  id: string;
  text: string;
  isAI: boolean;
  timestamp: Date;
}

interface ChatInterfaceProps {
  onCommand?: (command: string) => void;
  onWorkflowConfigComplete?: (config: any) => void;
  projectId?: number;
}

export function ChatInterface({ onCommand, onWorkflowConfigComplete, projectId = 1 }: ChatInterfaceProps) {
  const { session, createSession, sendMessage: sendWorkflowMessage, checkFinalization } = useWorkflowBuilder();
  const [inputValue, setInputValue] = useState('');
  const prevCompleteState = useRef(false);

  // Auto-trigger completion when finalization happens
  useEffect(() => {
    if (session.isComplete && !prevCompleteState.current && session.finalConfig) {
      prevCompleteState.current = true;

      // Auto-trigger the config completion after a short delay
      setTimeout(() => {
        if (onWorkflowConfigComplete) {
          onWorkflowConfigComplete(session.finalConfig);
        }
      }, 500);
    } else if (!session.isComplete) {
      prevCompleteState.current = false;
    }
  }, [session.isComplete, session.finalConfig, onWorkflowConfigComplete]);

  // Initialize chat session
  const createNewSession = async () => {
    try {
      await createSession(projectId);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  // Start session on mount with health check
  useEffect(() => {
    const initializeChat = async () => {
      try {
        // Check if FastAPI service is available
        const { WORKFLOW_BUILDER_CONFIG } = await import('../../lib/config');
        const isHealthy = await checkWorkflowBuilderHealth(WORKFLOW_BUILDER_CONFIG.BASE_URL);

        if (!isHealthy) {
          console.warn('Workflow Builder service is not available');
          // Still try to create session - user will see connection errors
        }

        await createNewSession();
      } catch (error) {
        console.error('Failed to initialize chat:', error);
      }
    };

    initializeChat();
  }, []);

  const handleSend = async () => {
    if (!session.sessionId || session.isLoading || !inputValue.trim()) return;

    const prompt = inputValue.trim();
    setInputValue('');

    // Process command for legacy compatibility
    onCommand?.(prompt);

    try {
      await sendWorkflowMessage(prompt);

      // Check if configuration is complete
      await checkFinalization();
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="border-t border-[#374151] p-4 flex flex-col">
      <div className="flex-grow space-y-4 mb-4 h-48 overflow-y-auto">
        {session.messages.length === 0 && !session.isLoading && (
          <div className="text-center py-4">
            <span className="material-symbols-outlined text-3xl text-gray-500 mb-2 block">smart_toy</span>
            <p className="text-gray-400 text-xs">
              Chat with AI to build your workflow structure
            </p>
          </div>
        )}

        {session.messages.map((message, index) => (
          <div key={index} className="flex items-start space-x-3">
            {message.role === 'model' ? (
              <div className="w-8 h-8 rounded-full bg-[#1173d4] flex-shrink-0 flex items-center justify-center text-white text-sm font-bold">
                AI
              </div>
            ) : (
              <div className="w-8 h-8 rounded-full bg-gray-600 flex-shrink-0 flex items-center justify-center text-white text-sm font-bold">
                U
              </div>
            )}
            <div className={`p-3 rounded-lg max-w-full ${
              message.role === 'model' ? 'bg-[#111a22]' : 'bg-[#1173d4]'
            }`}>
              <p className="text-sm text-white whitespace-pre-line">{message.content}</p>
              <span className="text-xs text-gray-400 mt-1 block">
                {new Date(message.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}

        {session.isLoading && (
          <div className="flex justify-start">
            <div className="bg-[#111a22] rounded-lg px-4 py-3">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {session.isComplete && session.finalConfig && (
        <div className="mb-2 p-2 bg-green-500/10 border border-green-500/20 rounded-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-green-400 text-sm">check_circle</span>
              <span className="text-xs text-green-400 font-medium">Workflow ready!</span>
            </div>
          </div>
        </div>
      )}

      <div className="relative">
        <Input
          type="text"
          placeholder={session.isLoading ? "Thinking..." : "Describe your workflow..."}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={session.isLoading || !session.sessionId || session.isComplete}
          className="w-full bg-[#111a22] border border-[#374151] rounded-full pl-4 pr-12 py-2 focus:ring-[#1173d4] focus:border-[#1173d4] text-sm text-white disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={session.isLoading || !session.sessionId || !inputValue.trim() || session.isComplete}
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-[#1173d4] text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-[#0f5aa3] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="material-symbols-outlined text-base">send</span>
        </button>
      </div>
    </div>
  );
}