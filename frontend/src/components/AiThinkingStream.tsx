// src/components/AiThinkingStream.tsx
"use client";

import React, { useState } from 'react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"; // from shadcn/ui
import { ChevronDown, Loader2 } from "lucide-react"; // Spinner icon
import ReactMarkdown, { Components as MarkdownComponents } from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

// Re-using markdown components from ChatMessage or define them here
const markdownComponents: MarkdownComponents = {
  p: ({ node: _node, ...props }) => <p className="mb-1 last:mb-0" {...props} />,
  code({ node: _node, inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '');
    return !inline && match ? (
      <pre className="bg-black/80 text-white p-3 rounded-md overflow-x-auto my-2 text-xs leading-relaxed">
        <code className={className} {...props}>{children}</code>
      </pre>
    ) : (
      <code className={cn("bg-black/10 dark:bg-white/10 px-1 py-0.5 rounded-sm text-xs text-foreground/80", className)} {...props}>{children}</code>
    );
  },
  ul: ({node: _node, ...props}) => <ul className="list-disc list-inside my-1 space-y-0.5 pl-2" {...props} />,
  ol: ({node: _node, ...props}) => <ol className="list-decimal list-inside my-1 space-y-0.5 pl-2" {...props} />,
  li: ({node: _node, ...props}) => <li className="pl-1" {...props} />,
};

interface AiThinkingStreamProps {
  streamedContent: string | null;
  isStreaming: boolean | undefined; // From message.isStreaming
  defaultOpen?: boolean; // To control if it starts open
}

export function AiThinkingStream({
  streamedContent,
  isStreaming,
  defaultOpen = true, // Let's default to open when content starts appearing
}: AiThinkingStreamProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  // Determine trigger text
  let triggerText = "AI's Thought Process";
  if (isStreaming && (!streamedContent || streamedContent.length < 20)) { // Show thinking if actively streaming and little content
    triggerText = "AI is thinking...";
  } else if (!isStreaming && streamedContent) {
    triggerText = "Show AI's Work";
  } else if (!streamedContent && !isStreaming) {
    triggerText = "AI Response (Empty)"; // Or some other placeholder
  }


return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full mt-1">
      <CollapsibleTrigger asChild>
        <button className="flex items-center justify-between w-full text-xs text-muted-foreground hover:text-foreground transition-colors py-1 px-2 rounded-md bg-muted/50 hover:bg-muted/80">
          {/* Text and Spinner Container - takes up available space */}
          <span className="flex-1 text-left flex items-center"> {/* Added flex-1 and text-left */}
            {triggerText}
            {isStreaming && <Loader2 className="h-3 w-3 animate-spin ml-2" />} {/* Moved spinner next to text */}
          </span>

          {/* Chevron Container - fixed position or pushed to the right */}
          <div className="flex-shrink-0"> {/* Prevents this div from shrinking */}
            <ChevronDown
              className={cn(
                "h-4 w-4 transition-transform duration-200", // Slightly larger for better click/visual
                isOpen && "rotate-180"
              )}
            />
          </div>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-2 pb-1 px-2 border-t border-border mt-1 rounded-b-md bg-background/30">
        {(!streamedContent && isStreaming) && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Generating response...</span>
          </div>
        )}
        {streamedContent && (
          <div className="prose prose-sm dark:prose-invert max-w-none"> {/* Basic prose styling for markdown */}
            <ReactMarkdown
              remarkPlugins={[remarkMath, remarkGfm]}
              rehypePlugins={[rehypeKatex, rehypeRaw]}
              components={markdownComponents}
            >
              {streamedContent}
            </ReactMarkdown>
          </div>
        )}
        {!streamedContent && !isStreaming && (
            <p className="text-xs text-muted-foreground italic py-2">No detailed steps provided or response was empty.</p>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
