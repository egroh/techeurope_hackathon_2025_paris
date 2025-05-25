// src/components/ChatMessage.tsx
"use client";

import React from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { OpenAIChatMessage, ToolCall } from '@/lib/apiTypes';
import { cn } from '@/lib/utils';
import { AiThinkingStream } from './AiThinkingStream';
// import 'katex/dist/katex.min.css';

interface ChatMessageProps {
  message: OpenAIChatMessage;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isHumanMessage = message.type === 'human';
  const isToolResponseMessage = message.type === 'tool_response';
  const isAiRequestingTool = message.type === 'ai' && message.tool_calls && message.tool_calls.length > 0;

  // Determine if we should show the "thinking" UI
  // Show if message.isThinking is explicitly true,
  // OR if it's an AI message that is currently streaming and isThinking is not explicitly false.
  // (Treat undefined/null isThinking as potentially thinking if it's a streaming AI message)
  const showThinkingUI =
    message.type === 'ai' &&
    !isAiRequestingTool && // Don't show for AI tool requests, they have their own UI
    (message.isThinkingProcess === true || (message.isStreaming && message.isThinkingProcess !== false));

  const markdownComponents: Components = {
    p: ({ node: _node, ...props }) => <p className="mb-1 last:mb-0" {...props} />,
    code({ node: _node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <pre className="bg-black/80 text-white p-3 rounded-md overflow-x-auto my-2 text-xs leading-relaxed">
          <code className={className} {...props}>{children}</code>
        </pre>
      ) : (
        <code className={cn("bg-black/10 dark:bg-white/10 px-1 py-0.5 rounded-sm text-xs", isHumanMessage ? "text-primary-foreground/80" : "text-foreground/80", className)} {...props}>{children}</code>
      );
    },
    ul: ({node: _node, ...props}) => <ul className="list-disc list-inside my-1 space-y-0.5 pl-2" {...props} />,
    ol: ({node: _node, ...props}) => <ol className="list-decimal list-inside my-1 space-y-0.5 pl-2" {...props} />,
    li: ({node: _node, ...props}) => <li className="pl-1" {...props} />,
  };

  return (
    <div
      className={cn(
        "flex w-fit max-w-[85%] md:max-w-[75%] flex-col gap-1 rounded-lg px-3 py-2 text-sm shadow-sm",
        isHumanMessage
          ? "ml-auto bg-primary text-primary-foreground rounded-br-none self-end"
          : isToolResponseMessage
          ? "bg-amber-100 dark:bg-amber-800/30 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-700 self-start rounded-tl-none"
          : isAiRequestingTool
          ? "bg-sky-100 dark:bg-sky-800/30 text-sky-900 dark:text-sky-200 border border-sky-300 dark:border-sky-700 self-start rounded-tl-none"
          : "bg-muted text-foreground self-start rounded-tl-none"
      )}
    >
      {/* If showThinkingUI is true, AiThinkingStream handles the content. */}
      {/* Otherwise, render content directly if it exists. */}
      {message.content && !showThinkingUI && (
        <ReactMarkdown
          remarkPlugins={[remarkMath, remarkGfm]}
          rehypePlugins={[rehypeKatex, rehypeRaw]}
          components={markdownComponents}
        >
          {message.content}
        </ReactMarkdown>
      )}

      {showThinkingUI && (
        <AiThinkingStream
          streamedContent={message.content}
          // Pass isStreaming to AiThinkingStream for its internal spinner logic
          // but the decision to show AiThinkingStream itself is based on message.isThinking
          isStreaming={message.isStreaming === true}
          defaultOpen={message.isThinkingProcess || (message.content && message.content.length > 0)}
        />
      )}

      {message.tool_calls && message.tool_calls.length > 0 && (
        <div className="mt-2 space-y-1 border-t border-current/20 pt-2">
          {message.tool_calls.map((tool_call: ToolCall, i: number) => (
            <div key={tool_call.id || i} className="text-xs opacity-80">
              <p className="font-semibold">Tool Call: {tool_call.function.name}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
