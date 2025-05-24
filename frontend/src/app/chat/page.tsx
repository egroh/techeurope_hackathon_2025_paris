// src/app/.../ChatPage.tsx (or wherever your component is)
"use client";

import { CardsChat } from "@/components/chat";
import { BaseMessage } from "@/lib/apiTypes";
import { useEffect, useState } from "react";

// Use the client-side environment variable for the WebSocket URL
const WS_URL =
  process.env.NEXT_PUBLIC_WS_BACKEND_URL || "ws://localhost:8000/api/chat"; // Fallback

export default function ChatPage() {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [messages, setMessages] = useState<Array<BaseMessage>>([]);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("connecting");

  useEffect(() => {
    console.log(`[ChatPage] Attempting to connect WebSocket to: ${WS_URL}`);
    const connectWebSocket = () => {
      const ws = new WebSocket(WS_URL);
      setSocket(ws);

      ws.onopen = () => {
        console.log("[ChatPage] WebSocket connected to server");
        setConnectionStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const data: BaseMessage = JSON.parse(event.data as string);
          setMessages((prevMessages) => [...prevMessages, data]);
        } catch (error) {
          console.error("[ChatPage] Error parsing WebSocket message:", error, event.data);
        }
      };

      ws.onclose = (event) => {
        console.log(
          `[ChatPage] WebSocket disconnected from server. Code: ${event.code}, Clean: ${event.wasClean}`
        );
        setConnectionStatus("disconnected");
        // More robust reconnection: only if not a clean close by client/server
        if (!event.wasClean || (event.code !== 1000 && event.code !== 1005)) {
            console.log("[ChatPage] Attempting to reconnect WebSocket...");
            setTimeout(connectWebSocket, 3000);
        }
      };

      ws.onerror = (error) => {
        console.error("[ChatPage] WebSocket error:", error);
        // ws.close(); // onclose will usually be triggered after an error that closes the socket
      };
    };

    connectWebSocket();

    return () => {
      if (socket) {
        console.log("[ChatPage] Closing WebSocket on component unmount.");
        socket.onclose = null; // Prevent reconnection logic from firing
        socket.close(1000, "Component unmounted"); // Normal closure
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty dependency array ensures this runs once on mount

  const userSentMessage = (message: string) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({
          content: message,
        })
      );
    } else {
      console.warn(
        "[ChatPage] WebSocket not open. Message not sent:",
        message
      );
    }
  };

  return (
    <div>
      <div className="p-2 text-sm">
        Status:{" "}
        {connectionStatus === "connected"
          ? "🟢 Connected"
          : connectionStatus === "connecting"
          ? "🟡 Connecting..."
          : "🔴 Disconnected"}
      </div>
      <CardsChat
        messages={messages}
        onSendMessage={(message: string) => {
          userSentMessage(message);
        }}
      />
    </div>
  );
}
