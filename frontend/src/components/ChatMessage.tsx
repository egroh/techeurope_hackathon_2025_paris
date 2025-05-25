// src/components/ChatMessage.tsx
"use client";

import React from 'react';
import ReactMarkdown from 'react-markdown'; // Import Components type
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { OpenAIChatMessage, ToolCall } from '@/lib/apiTypes'; // Assuming ToolCall is defined in apiTypes
import { cn } from '@/lib/utils';
import { AiThinkingStream } from './AiThinkingStream'; // Import the new component
// import 'katex/dist/katex.min.css'; // Ensure loaded globally

interface ChatMessageProps {
  message: OpenAIChatMessage;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isHumanMessage = message.type === 'human';
  const isToolResponseMessage = message.type === 'tool_response';
  const isAiRequestingTool = message.type === 'ai' && message.tool_calls && message.tool_calls.length > 0;
  // An AI message that is NOT a tool request could be a simple text response or a streamed response
  const isStreamableAiMessage = message.type === 'ai' && !isAiRequestingTool;

  // If it's an AI message that was streamed (or is streaming), use AiThinkingStream
  // We can identify streamed messages if they have a message_id (set at stream start)
  // or if isStreaming is true.
  const showThinkingStream = isStreamableAiMessage && (message.message_id || message.isStreaming !== undefined);

  return (
    <div
      className={cn(
        "flex w-fit max-w-[85%] md:max-w-[75%] flex-col gap-1 rounded-lg px-3 py-2 text-sm shadow-sm",
        isHumanMessage
          ? "ml-auto bg-primary text-primary-foreground rounded-br-none self-end"
          : isToolResponseMessage
          ? "bg-amber-100 dark:bg-amber-800/30 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-700 self-start rounded-tl-none"
          : isAiRequestingTool // AI asking to call a tool (shows tool_calls)
          ? "bg-sky-100 dark:bg-sky-800/30 text-sky-900 dark:text-sky-200 border border-sky-300 dark:border-sky-700 self-start rounded-tl-none"
          : "bg-muted text-foreground self-start rounded-tl-none" // Default AI (could be simple or streamed)
      )}
    >
      {/* Render primary content:
          - For human messages: direct content (could be Markdown if users can input it)
          - For AI tool requests: the preliminary content before tool calls
          - For simple AI non-streamed text: direct content
          - For tool_response: direct content (tool's output)
          - For streamed AI: This part might be a summary or initial prompt,
            the detailed stream goes into AiThinkingStream.
            Let's assume for now that if showThinkingStream is true, the main content
            is handled by AiThinkingStream. If there's also a top-level message.content
            for a streamed message (e.g. "Okay, I will solve that for you:"), render it.
      */}
      {message.content && !showThinkingStream && (
         <ReactMarkdown /* Basic Markdown for non-streamed AI or human messages if needed */
            remarkPlugins={[remarkMath, remarkGfm]}
            rehypePlugins={[rehypeKatex, rehypeRaw]}
            // You might want simpler markdownComponents here if AiThinkingStream has the full ones
            components={{ p: ({node: _node, ...props}) => <p className="mb-0" {...props} /> }}
         >
          {message.content}
        </ReactMarkdown>
      )}
      {/* If it's an AI message that is NOT a tool request, and it has a message_id (meaning it was streamed)
          OR if it's currently streaming, then show the AiThinkingStream component.
          The content for AiThinkingStream will be message.content which is accumulated in ChatPage.
      */}
      {showThinkingStream && (
        <AiThinkingStream
          streamedContent={message.content}
          isStreaming={message.isStreaming}
          // Default open if it's currently streaming or just finished and has content
          defaultOpen={message.isStreaming || (message.content && message.content.length > 0)}
        />
      )}

      {/* Display tool calls if they exist (typically for AI messages requesting a tool) */}
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
