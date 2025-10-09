import { useState, useEffect, useRef } from 'react';
import { api } from '../../lib/api';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';

// Generate a unique session ID using modern browser API
function generateSessionId(): string {
  return crypto.randomUUID();
}

interface Message {
  id: string;
  type: 'user' | 'status' | 'result' | 'error' | 'bot';
  content: string;
  data?: any;
  timestamp: Date;
}

interface WorkflowTriggerChatProps {
  workflowId: number;
  onClose: () => void;
  welcomeMessage?: string;
}

export function WorkflowTriggerChat({ workflowId, onClose, welcomeMessage }: WorkflowTriggerChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [executionId, setExecutionId] = useState<number | null>(null);
  const [sessionId, setSessionId] = useState<string>(() => generateSessionId());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Show welcome message on mount
  useEffect(() => {
    if (welcomeMessage) {
      setMessages([{
        id: 'welcome',
        type: 'status',
        content: welcomeMessage,
        timestamp: new Date()
      }]);
    }
  }, [welcomeMessage]);

  // Poll execution status
  const startPolling = (execId: number) => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }

    pollingRef.current = setInterval(async () => {
      try {
        const status = await api.getExecutionStatus(execId);

        if (status.status === 'completed') {
          // Check if this is a chat-triggered workflow with bot response
          if (status.chat_response) {
            setMessages(prev => [...prev, {
              id: `bot-${execId}`,
              type: 'bot',
              content: status.chat_response,
              timestamp: new Date()
            }]);
          } else {
            // Fallback to result message for non-chat workflows
            setMessages(prev => [...prev, {
              id: `result-${execId}`,
              type: 'result',
              content: 'Workflow completed successfully',
              data: status.execution_log || status.results,
              timestamp: new Date()
            }]);
          }
          setIsLoading(false);
          setExecutionId(null);
          if (pollingRef.current) clearInterval(pollingRef.current);
        } else if (status.status === 'failed') {
          setMessages(prev => [...prev, {
            id: `error-${execId}`,
            type: 'error',
            content: status.error_message || 'Workflow execution failed',
            timestamp: new Date()
          }]);
          setIsLoading(false);
          setExecutionId(null);
          if (pollingRef.current) clearInterval(pollingRef.current);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000); // Poll every 2 seconds
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');

    // Add user message
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: userMessage,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    // Add status message
    setMessages(prev => [...prev, {
      id: `status-${Date.now()}`,
      type: 'status',
      content: 'Executing workflow...',
      timestamp: new Date()
    }]);

    setIsLoading(true);

    try {
      // Trigger workflow via chat with session_id to maintain conversation context
      const result = await api.triggerWorkflowViaChat(workflowId, userMessage, sessionId);
      setExecutionId(result.execution_id);

      // Start polling for execution status
      startPolling(result.execution_id);
    } catch (error: any) {
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        type: 'error',
        content: error.detail || 'Failed to trigger workflow',
        timestamp: new Date()
      }]);
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleStartNewChat = () => {
    // Generate new session_id for fresh conversation
    setSessionId(generateSessionId());
    setMessages(welcomeMessage ? [{
      id: 'welcome',
      type: 'status',
      content: welcomeMessage,
      timestamp: new Date()
    }] : []);
    setExecutionId(null);
    setIsLoading(false);
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
  };

  const renderMessage = (message: Message) => {
    switch (message.type) {
      case 'user':
        return (
          <div key={message.id} className="flex justify-end">
            <div className="bg-[#1173d4] rounded-lg px-4 py-2 max-w-[80%]">
              <p className="text-sm text-white whitespace-pre-wrap">{message.content}</p>
              <span className="text-xs text-gray-300 mt-1 block">
                {message.timestamp.toLocaleTimeString()}
              </span>
            </div>
          </div>
        );

      case 'status':
        return (
          <div key={message.id} className="flex justify-center">
            <div className="bg-[#111a22] border border-[#374151] rounded-lg px-4 py-2 inline-block">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                <p className="text-sm text-gray-300">{message.content}</p>
              </div>
            </div>
          </div>
        );

      case 'result':
        return (
          <div key={message.id} className="flex justify-start">
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-3 max-w-[85%]">
              <div className="flex items-start gap-2 mb-2">
                <span className="material-symbols-outlined text-green-400 text-lg">check_circle</span>
                <p className="text-sm text-green-400 font-medium">{message.content}</p>
              </div>
              {message.data && (
                <div className="mt-2 bg-[#111a22] rounded p-3 overflow-auto max-h-60">
                  <pre className="text-xs text-gray-300 whitespace-pre-wrap">
                    {JSON.stringify(message.data, null, 2)}
                  </pre>
                </div>
              )}
              <span className="text-xs text-gray-400 mt-2 block">
                {message.timestamp.toLocaleTimeString()}
              </span>
            </div>
          </div>
        );

      case 'bot':
        return (
          <div key={message.id} className="flex justify-start">
            <div className="bg-[#111a22] border border-[#374151] rounded-lg px-4 py-3 max-w-[85%]">
              <div className="flex items-start gap-2 mb-1">
                <span className="material-symbols-outlined text-purple-400 text-lg">smart_toy</span>
                <span className="text-xs font-medium text-purple-400">Workflow Assistant</span>
              </div>
              <div className="ml-7">
                <p className="text-sm text-gray-200 whitespace-pre-wrap">{message.content}</p>
                <span className="text-xs text-gray-400 mt-2 block">
                  {message.timestamp.toLocaleTimeString()}
                </span>
              </div>
            </div>
          </div>
        );

      case 'error':
        return (
          <div key={message.id} className="flex justify-start">
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 max-w-[85%]">
              <div className="flex items-start gap-2">
                <span className="material-symbols-outlined text-red-400 text-lg">error</span>
                <div>
                  <p className="text-sm text-red-400">{message.content}</p>
                  <span className="text-xs text-gray-400 mt-1 block">
                    {message.timestamp.toLocaleTimeString()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#1a2633] border-l border-[#374151]">
      {/* Header */}
      <div className="p-4 border-b border-[#374151] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-purple-400">chat</span>
          <h3 className="text-white font-semibold">Chat Trigger</h3>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white transition-colors"
          title="Close chat"
        >
          <span className="material-symbols-outlined">close</span>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-grow overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <span className="material-symbols-outlined text-4xl text-gray-500 mb-2 block">forum</span>
            <p className="text-gray-400 text-sm">Send a message to trigger the workflow</p>
          </div>
        )}
        {messages.map(renderMessage)}
        <div ref={messagesEndRef} />
      </div>

      {/* Actions */}
      {messages.length > 0 && !isLoading && (
        <div className="px-4 py-2 border-t border-[#374151]">
          <Button
            size="sm"
            variant="outline"
            onClick={handleStartNewChat}
            className="w-full"
            leftIcon={<span className="material-symbols-outlined text-sm">refresh</span>}
          >
            Start New Chat
          </Button>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-[#374151]">
        <div className="relative">
          <Input
            type="text"
            placeholder={isLoading ? "Workflow executing..." : "Type your message..."}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
            className="w-full bg-[#111a22] border-[#374151] pr-12 text-white disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-purple-500 text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-purple-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-base">send</span>
          </button>
        </div>
      </div>
    </div>
  );
}
