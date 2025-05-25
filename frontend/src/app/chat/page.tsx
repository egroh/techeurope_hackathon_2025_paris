"use client";

import {Chat} from "@/components/ChatCards"; // Assuming this is your shadcn/ui chat component
import { OpenAIChatMessage } from "@/lib/apiTypes"; // Your updated type
import { useEffect, useState, useRef } from "react";
import { v4 as uuidv4 } from "uuid";

const WS_URL =
  process.env.NEXT_PUBLIC_WS_BACKEND_URL || "ws://localhost:8000/api/chat";

export default function ChatPage() {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [messages, setMessages] = useState<Array<OpenAIChatMessage>>([]);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("connecting");
  const currentConversationId = useRef<string | null>(null); // To store conversation ID

  useEffect(() => {
    console.log(`[ChatPage] Attempting to connect WebSocket to: ${WS_URL}`);
    const connectWebSocket = () => {
      const ws = new WebSocket(WS_URL);
      setSocket(ws);
      setConnectionStatus("connecting");

      ws.onopen = () => {
        console.log("[ChatPage] WebSocket connected to server");
        setConnectionStatus("connected");
        // You could generate a conversation ID here or expect one from the server
        // For now, we'll let the server assign one per connection.
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data as string) as OpenAIChatMessage; // Cast to your updated type
          console.log("[ChatPage] Received data:", data);

          if (!currentConversationId.current && data.conversation_id) {
            currentConversationId.current = data.conversation_id;
          }

          setMessages((prevMessages) => {
            if (data.type === "ai" && data.message_id) {
              if (data.stream_event === "start") {
                // AI message stream starts, add a new message placeholder
                return [
                  ...prevMessages,
                  {
                    ...data,
                    id: data.message_id, // Use AI message_id as the key for this message
                    content: data.content || "", // Start with initial content or empty
                    isStreaming: true,
                  },
                ];
              } else if (data.stream_event === "chunk") {
                // AI message chunk, append to existing message
                return prevMessages.map((msg) =>
                  msg.id === data.message_id // Match by the AI's response ID
                    ? {
                        ...msg,
                        content: (msg.content || "") + (data.content || ""),
                        isStreaming: true,
                      }
                    : msg
                );
              } else if (data.stream_event === "end") {
                // AI message stream ends
                return prevMessages.map((msg) =>
                  msg.id === data.message_id
                    ? { ...msg, isStreaming: false }
                    : msg
                );
              }
            }
            // For non-streaming messages or other types (errors, user echos if implemented)
            // Ensure each message has a unique 'id' for React keys
            return [...prevMessages, { ...data, id: data.id || uuidv4() }];
          });
        } catch (error) {
          console.error(
            "[ChatPage] Error parsing WebSocket message:",
            error,
            event.data
          );
          // Add an error message to the chat UI
          setMessages((prev) => [
            ...prev,
            {
              id: uuidv4(),
              type: "error",
              content: "Error processing message from server.",
              conversation_id: currentConversationId.current || "unknown",
            },
          ]);
        }
      };

      ws.onclose = (event) => {
        console.log(
          `[ChatPage] WebSocket disconnected. Code: ${event.code}, Clean: ${event.wasClean}, Reason: ${event.reason}`
        );
        setConnectionStatus("disconnected");
        if (!event.wasClean && event.code !== 1000 && event.code !== 1005) {
          console.log("[ChatPage] Attempting to reconnect WebSocket...");
          setTimeout(connectWebSocket, 3000); // Reconnect after 3 seconds
        }
      };

      ws.onerror = (errorEvent) => {
        console.error("[ChatPage] WebSocket error:", errorEvent);
        setConnectionStatus("disconnected"); // Often onclose is called too
        // ws.close(); // onclose will usually be triggered
      };
    };

    connectWebSocket();

    return () => {
      if (socket) {
        console.log("[ChatPage] Closing WebSocket on component unmount.");
        socket.onclose = null; // Prevent reconnection logic
        socket.close(1000, "Component unmounted");
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty dependency array: runs once on mount

  const userSentMessage = (messageContent: string) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      const userMessage: OpenAIChatMessage = {
        id: uuidv4(), // Client-side unique ID for this message
        type: "human",
        content: messageContent,
        conversation_id: currentConversationId.current || "new_conversation", // Send current or indicate new
      };

      // Add user message to UI immediately for responsiveness
      setMessages((prevMessages) => [...prevMessages, userMessage]);

      // Send to backend (backend schema PostUserMessage only needs content)
      socket.send(
        JSON.stringify({
          content: messageContent,
          // conversation_id: currentConversationId.current // Optional: if backend uses it to resume
        })
      );
    } else {
      console.warn(
        "[ChatPage] WebSocket not open. Message not sent:",
        messageContent
      );
      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          type: "error",
          content: "Cannot send message: Not connected to server.",
          conversation_id: currentConversationId.current || "unknown",
        },
      ]);
    }
  };

  return (
    <div>
      <div className="p-2 text-sm border-b mb-2">
        Status:{" "}
        <span
          className={
            connectionStatus === "connected"
              ? "text-green-500"
              : connectionStatus === "connecting"
              ? "text-yellow-500"
              : "text-red-500"
          }
        >
          {connectionStatus === "connected"
            ? "🟢 Connected"
            : connectionStatus === "connecting"
            ? "🟡 Connecting..."
            : "🔴 Disconnected"}
        </span>
        {currentConversationId.current && (
          <span className="ml-4 text-xs text-gray-500">
            Conv ID: {currentConversationId.current}
          </span>
        )}
      </div>
      <Chat
        messages={messages}
        onSendMessage={(message: string) => {
          userSentMessage(message);
        }}
        // You might need to pass down the current user ID if CardsChat needs it
        // userId="current_user_id_placeholder"
        // isLoading={messages.some(msg => msg.isStreaming)} // Optional: pass a global loading state
      />
    </div>
  );
}
