import { useState } from 'react';
import { Input } from '../ui/Input';

interface ChatMessage {
  id: number;
  text: string;
  isAI: boolean;
  timestamp: Date;
}

interface ChatInterfaceProps {
  onCommand?: (command: string) => void;
}

export function ChatInterface({ onCommand }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      text: "Hello! How can I help you build your workflow today? You can ask me to add nodes, connect them, or modify their settings.",
      isAI: true,
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');

  const handleSend = () => {
    if (!inputValue.trim()) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now(),
      text: inputValue,
      isAI: false,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);

    // Process command
    onCommand?.(inputValue);

    // Add AI response (simplified for now)
    setTimeout(() => {
      const aiResponse: ChatMessage = {
        id: Date.now() + 1,
        text: getAIResponse(inputValue),
        isAI: true,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiResponse]);
    }, 1000);

    setInputValue('');
  };

  const getAIResponse = (command: string): string => {
    const lowerCommand = command.toLowerCase();

    if (lowerCommand.includes('add') && lowerCommand.includes('database')) {
      return "I'll add a database node for you. Drag the Database node from the Data section to your canvas.";
    }
    if (lowerCommand.includes('add') && lowerCommand.includes('agent')) {
      return "Perfect! Drag the Agent Node from the Agents section to process your data.";
    }
    if (lowerCommand.includes('connect')) {
      return "To connect nodes, drag from the blue handle on the right of one node to the left handle of another node.";
    }
    if (lowerCommand.includes('config') || lowerCommand.includes('configure')) {
      return "You can view the current workflow configuration using the config toggle button. Node configurations will be available soon!";
    }
    if (lowerCommand.includes('help')) {
      return "Here's what you can do:\n• Drag nodes from the sidebar\n• Connect nodes by dragging between handles\n• Delete nodes with the X button or Del key\n• Ask me to add specific nodes or explain features";
    }

    return "I understand you want to work on your workflow. Try dragging nodes from the sidebar or ask me to help with specific tasks!";
  };

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
              <span className="text-xs text-gray-400 mt-1 block">
                {message.timestamp.toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="relative">
        <Input
          type="text"
          placeholder="Chat to build..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          className="w-full bg-[#111a22] border border-[#374151] rounded-full pl-4 pr-12 py-2 focus:ring-[#1173d4] focus:border-[#1173d4] text-sm text-white"
        />
        <button
          onClick={handleSend}
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-[#1173d4] text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-[#0f5aa3] transition-colors"
        >
          <span className="material-symbols-outlined text-base">send</span>
        </button>
      </div>
    </div>
  );
}