// src/components/ChatMessage.tsx

"use client";

import React from 'react';
import ReactMarkdown, { Components } from 'react-markdown'; // Import Components type
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { OpenAIChatMessage, ToolCall } from '@/lib/apiTypes'; // Assuming ToolCall is defined in apiTypes
import { cn } from '@/lib/utils';

interface ChatMessageProps {
  message: OpenAIChatMessage;
}

export function ChatMessage({ message }: ChatMessageProps) {
  // Your existing logic for determining message styling
  const isHumanMessage = message.type === 'human';
  const isToolMessage = message.type === 'tool_response'; // Assuming 'tool_response' for tool results
  const isAiRequestingTool = message.type === 'ai' && message.tool_calls && message.tool_calls.length > 0;

  const markdownComponents: Components = { // Use the imported Components type
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    p: ({ node: _node, ...props }) => <p className="mb-1 last:mb-0" {...props} />,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    code({ node: _node, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      return match ? (
        <pre className="bg-black/80 text-white p-3 rounded-md overflow-x-auto my-2 text-xs leading-relaxed">
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      ) : (
        <code
          className={cn(
            "bg-black/10 dark:bg-white/10 px-1 py-0.5 rounded-sm text-xs",
            isHumanMessage ? "text-primary-foreground/80" : "text-foreground/80", // Adjust color based on bubble
            className
          )}
          {...props}
        >
          {children}
        </code>
      );
    },
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    ul: ({node: _node, ...props}) => <ul className="list-disc list-inside my-1 space-y-0.5 pl-2" {...props} />,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    ol: ({node: _node, ...props}) => <ol className="list-decimal list-inside my-1 space-y-0.5 pl-2" {...props} />,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    li: ({node: _node, ...props}) => <li className="pl-1" {...props} />,
    // You can add custom renderers for <table>, <th>, <td>, <tr> if needed for tool outputs
    // Or if your <step N> tags are actual HTML, rehypeRaw will handle them.
    // If they are custom like <step1>, you might need a custom component or ask AI to use Markdown.
  };

  return (
    <div
      className={cn(
        "flex w-fit max-w-[85%] md:max-w-[75%] flex-col gap-1 rounded-lg px-3 py-2 text-sm shadow-sm", // Common styling
        isHumanMessage
          ? "ml-auto bg-primary text-primary-foreground rounded-br-none self-end"
          : isToolMessage
          ? "bg-amber-100 dark:bg-amber-800/30 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-700 self-start rounded-tl-none" // Style for tool responses
          : isAiRequestingTool
          ? "bg-sky-100 dark:bg-sky-800/30 text-sky-900 dark:text-sky-200 border border-sky-300 dark:border-sky-700 self-start rounded-tl-none" // Style for AI messages that are tool requests
          : "bg-muted text-foreground self-start rounded-tl-none" // Default AI or system message
      )}
    >
      {/* Render message content using ReactMarkdown */}
      {message.content && ( // Only render ReactMarkdown if there's content
        <ReactMarkdown
          remarkPlugins={[remarkMath, remarkGfm]}
          rehypePlugins={[rehypeKatex, rehypeRaw]}
          components={markdownComponents}
        >
          {message.content}
        </ReactMarkdown>
      )}

      {/* Display tool calls if they exist (typically for AI messages requesting a tool) */}
      {message.tool_calls && message.tool_calls.length > 0 && (
        <div className="mt-2 space-y-1 border-t border-current/20 pt-2">
          {message.tool_calls.map((tool_call: ToolCall, i: number) => ( // Added ToolCall type
            <div key={tool_call.id || i} className="text-xs opacity-80">
              <p className="font-semibold">Tool Call: {tool_call.function.name}</p>
              {/* Optionally display arguments, be careful if they are large */}
              {/* <pre className="text-xs whitespace-pre-wrap bg-black/5 p-1 rounded">
                Args: {tool_call.function.arguments}
              </pre> */}
            </div>
          ))}
        </div>
      )}

      {/* Display content if message type is 'tool_response' (this is where tool output would go) */}
      {/* The above ReactMarkdown already handles message.content. If tool_response has specific structured output,
          you might render it differently or expect it within message.content as Markdown/HTML.
          If message.content IS the tool's output for a 'tool_response' type, then the ReactMarkdown above handles it.
      */}
    </div>
  );
}
