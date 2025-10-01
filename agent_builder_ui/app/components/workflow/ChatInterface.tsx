import { useState, useEffect, useRef } from 'react';
import { Input } from '../ui/Input';
import { agentBuilderApi, type AgentBuilderMessage, type AgentConfig } from '../../lib/agentBuilderApi';

interface ChatMessage {
  id: string;
  text: string;
  isAI: boolean;
  timestamp: Date;
}

interface ChatInterfaceProps {
  onCommand?: (command: string) => void;
  onAgentConfigured?: (config: AgentConfig) => void;
}

export function ChatInterface({ onCommand, onAgentConfigured }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isInitialized, setIsInitialized] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const abortControllerRef = useRef<AbortController | null>(null);

  // Initialize session on client side only
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const session = await agentBuilderApi.createSession();
        setSessionId(session.session_id);
        setMessages([
          {
            id: 'welcome',
            text: "Hello! I'll help you create an AI agent. Tell me what you want your agent to do, and I'll ask focused questions to build the perfect configuration.",
            isAI: true,
            timestamp: new Date(),
          },
        ]);
        setIsInitialized(true);
      } catch (error) {
        console.error('Failed to initialize session:', error);
        setMessages([
          {
            id: 'error',
            text: "Sorry, I couldn't connect to the agent builder service. Please check if the service is running.",
            isAI: true,
            timestamp: new Date(),
          },
        ]);
        setIsInitialized(true);
      }
    };

    initializeSession();
  }, []);

  const handleSend = async () => {
    if (!inputValue.trim() || !sessionId || isLoading) return;

    const prompt = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    // Add user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      text: prompt,
      isAI: false,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);

    // Process command for legacy compatibility
    onCommand?.(prompt);

    try {
      // Create abort controller for this request
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      // Start streaming response
      let currentResponse = '';
      let responseId = `ai-${Date.now()}`;

      // Add initial AI message
      const initialAiMessage: ChatMessage = {
        id: responseId,
        text: '',
        isAI: true,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, initialAiMessage]);

      // Stream the response
      for await (const message of agentBuilderApi.generateStream(prompt, sessionId)) {
        if (abortController.signal.aborted) break;

        if (message.role === 'model') {
          currentResponse = message.content;
          setMessages(prev =>
            prev.map(msg =>
              msg.id === responseId
                ? { ...msg, text: currentResponse }
                : msg
            )
          );
        }
      }

      // Check if we have a finalized agent config
      setTimeout(async () => {
        try {
          const config = await agentBuilderApi.finalizeAgentConfig(sessionId);
          if (config && onAgentConfigured) {
            onAgentConfigured(config);
          }
        } catch (error) {
          console.error('Failed to check for finalized config:', error);
        }
      }, 1000);

    } catch (error) {
      console.error('Failed to send message:', error);

      // Add error message
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        text: "Sorry, I encountered an error. Please try again.",
        isAI: true,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  // Cleanup function for aborting requests
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="border-t border-[#374151] p-4 flex flex-col">
      <div className="flex-grow space-y-4 mb-4 h-48 overflow-y-auto">
        {messages.map((message) => (
          <div key={message.id} className="flex items-start space-x-3">
            {message.isAI ? (
              <div className="w-8 h-8 rounded-full bg-[#1173d4] flex-shrink-0 flex items-center justify-center text-white text-sm font-bold">
                AI
              </div>
            ) : (
              <div className="w-8 h-8 rounded-full bg-gray-600 flex-shrink-0 flex items-center justify-center text-white text-sm font-bold">
                U
              </div>
            )}
            <div className={`p-3 rounded-lg max-w-full ${
              message.isAI ? 'bg-[#111a22]' : 'bg-[#1173d4]'
            }`}>
              <p className="text-sm text-white whitespace-pre-line">{message.text}</p>
              {isInitialized && (
                <span className="text-xs text-gray-400 mt-1 block">
                  {message.timestamp.toLocaleTimeString()}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="relative">
        <Input
          type="text"
          placeholder={isLoading ? "Thinking..." : "Describe what you want your agent to do..."}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isLoading || !sessionId}
          className="w-full bg-[#111a22] border border-[#374151] rounded-full pl-4 pr-12 py-2 focus:ring-[#1173d4] focus:border-[#1173d4] text-sm text-white disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !sessionId || !inputValue.trim()}
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-[#1173d4] text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-[#0f5aa3] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="material-symbols-outlined text-base">send</span>
        </button>
      </div>
    </div>
  );
}