import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
        // Tables
        table: ({ node, ...props }) => (
          <div className="overflow-x-auto my-4">
            <table className="min-w-full border-collapse border border-gray-600" {...props} />
          </div>
        ),
        thead: ({ node, ...props }) => (
          <thead className="bg-gray-700" {...props} />
        ),
        tbody: ({ node, ...props }) => (
          <tbody className="divide-y divide-gray-600" {...props} />
        ),
        tr: ({ node, ...props }) => (
          <tr className="hover:bg-gray-700/30" {...props} />
        ),
        th: ({ node, ...props }) => (
          <th className="px-4 py-2 text-left text-sm font-semibold text-gray-200 border border-gray-600" {...props} />
        ),
        td: ({ node, ...props }) => (
          <td className="px-4 py-2 text-sm text-gray-300 border border-gray-600" {...props} />
        ),

        // Code blocks
        code: ({ node, inline, className, children, ...props }: any) => {
          const match = /language-(\w+)/.exec(className || '');
          return !inline ? (
            <pre className="bg-gray-900 rounded-md p-4 overflow-x-auto my-3 border border-gray-700">
              <code className={className} {...props}>
                {children}
              </code>
            </pre>
          ) : (
            <code className="bg-gray-800 px-1.5 py-0.5 rounded text-sm font-mono text-gray-200" {...props}>
              {children}
            </code>
          );
        },

        // Headings
        h1: ({ node, ...props }) => (
          <h1 className="text-2xl font-bold text-white mt-6 mb-3" {...props} />
        ),
        h2: ({ node, ...props }) => (
          <h2 className="text-xl font-bold text-white mt-5 mb-2" {...props} />
        ),
        h3: ({ node, ...props }) => (
          <h3 className="text-lg font-semibold text-white mt-4 mb-2" {...props} />
        ),

        // Lists
        ul: ({ node, ...props }) => (
          <ul className="list-disc list-inside space-y-1 my-3 text-gray-300" {...props} />
        ),
        ol: ({ node, ...props }) => (
          <ol className="list-decimal list-inside space-y-1 my-3 text-gray-300" {...props} />
        ),
        li: ({ node, ...props }) => (
          <li className="text-gray-300" {...props} />
        ),

        // Blockquotes
        blockquote: ({ node, ...props }) => (
          <blockquote className="border-l-4 border-gray-600 pl-4 italic text-gray-400 my-3" {...props} />
        ),

        // Links
        a: ({ node, ...props }) => (
          <a className="text-blue-400 hover:text-blue-300 underline" target="_blank" rel="noopener noreferrer" {...props} />
        ),

        // Paragraphs
        p: ({ node, ...props }) => (
          <p className="text-gray-300 my-2" {...props} />
        ),

        // Horizontal rules
        hr: ({ node, ...props }) => (
          <hr className="border-gray-600 my-4" {...props} />
        ),

        // Strong/Bold
        strong: ({ node, ...props }) => (
          <strong className="font-semibold text-white" {...props} />
        ),

        // Emphasis/Italic
        em: ({ node, ...props }) => (
          <em className="italic text-gray-200" {...props} />
        ),
      }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
