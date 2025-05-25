// src/components/chat.tsx (This is effectively your CardsChat)

"use client";

import { Send } from "lucide-react";
import * as React from "react";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { v4 as uuidv4 } from "uuid"; // Keep for fallback key if needed

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { OpenAIChatMessage } from "@/lib/apiTypes";
import { ChatMessage } from "@/components/ChatMessage"; // <--- IMPORTING THE SINGLE MESSAGE RENDERER

interface ChatProps { // Renamed from CardsChatProps to ChatProps to match component name
  messages: Array<OpenAIChatMessage>;
  onSendMessage: (message: string) => void;

  taskTypeSelector?: React.ReactNode;

}

export function Chat({ messages, onSendMessage, taskTypeSelector }: ChatProps) {
  const [input, setInput] = React.useState("");
  const messagesEndRef = React.useRef<HTMLDivElement | null>(null);
  const inputLength = input.trim().length;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  React.useEffect(() => {
    if (messages.length > 0) {
        scrollToBottom();
    }
  }, [messages]);

  return (
    <Card className="flex flex-col w-full h-[calc(100vh-150px)] md:h-[calc(100vh-120px)] shadow-xl">
      <CardHeader className="w-full py-3 border-b sticky top-0 bg-card z-10">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
          <h2 className="text-lg font-semibold text-accent-foreground text-center md:text-left">
            Mathstral Chat
          </h2>

          {/* Render dropdown + toggle in header */}
          {taskTypeSelector && (
            <div className="w-full md:w-auto">{taskTypeSelector}</div>
          )}
        </div>
      </CardHeader>


      <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">

        {messages.map((message: OpenAIChatMessage) => (
          <ChatMessage
            // Use a stable unique ID from the message object itself for the key
            // message.id is good if client generates for user messages & server sends for AI stream start
            // message.message_id is good if it's the unique ID for an AI response stream
            // Fallback to uuidv4() only if absolutely no other stable ID is available,
            // but this can lead to issues with React's reconciliation if items reorder or change.
            key={message.id || message.message_id || uuidv4()}
            message={message}
          />
        ))}
        <div ref={messagesEndRef} />
      </CardContent>

      <CardFooter className="p-4 border-t sticky bottom-0 bg-card z-10">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (inputLength === 0) return;
            onSendMessage(input);
            setInput("");
          }}
          className="flex w-full items-center space-x-2"
        >
          <Input
            id="message"
            placeholder="Ask a math question..."
            className="flex-1"
            autoComplete="off"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                if (inputLength === 0) return;
                onSendMessage(input);
                setInput("");
              }
            }}
          />
          <Button type="submit" size="icon" disabled={inputLength === 0}>
            <Send className="h-4 w-4" />
            <span className="sr-only">Send</span>
          </Button>
        </form>
      </CardFooter>
    </Card>
  );
}
