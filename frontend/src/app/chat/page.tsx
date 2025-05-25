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

  const [taskType, setTaskType] = useState("abstract");
  const [reduceHallucinations, setReduceHallucinations] = useState(false);

  const handleTaskTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = e.target.value;
    setTaskType(selected);

    if (!["abstract", "functional"].includes(selected)) {
      setReduceHallucinations(false);
    }
  };


  const toggleHallucinations = () => {
    setReduceHallucinations((prev) => !prev);
  };

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
            if (data.type === "ai" && data.message_id) { // AI message part of a stream
              if (data.stream_event === "start") {
                return [
                  ...prevMessages,
                  {
                    ...data, // This will include data.isThinking if sent by backend
                    id: data.message_id,
                    content: data.content || "",
                    isStreaming: true,
                    // isThinking is directly from 'data' if backend sends it
                  },
                ];
              } else if (data.stream_event === "chunk") {
                return prevMessages.map((msg) =>
                  msg.id === data.message_id
                    ? {
                        ...msg,
                        content: (msg.content || "") + (data.content || ""),
                        isStreaming: true, // Keep streaming true
                        // isThinking should remain true, backend might not resend it with every chunk
                        // If backend sends isThinking with chunks, it will be in 'data' and spread:
                        ...(data.isThinkingProcess !== undefined && { isThinking: data.isThinkingProcess }),
                      }
                    : msg
                );
              } else if (data.stream_event === "end") {
                return prevMessages.map((msg) =>
                  msg.id === data.message_id
                    ? {
                        ...msg,
                        isStreaming: false,
                        isThinking: false, // Explicitly set isThinking to false on stream end
                        // If backend sends final content with 'end' event, spread 'data'
                        ...(data.content && { content: (msg.content || "") + data.content }),
                      }
                    : msg
                );
              }
            }
            // For non-streamed messages (e.g., a complete AI response sent at once)
            // or other message types. Ensure 'isThinking' from 'data' is included.
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
          task_type: taskType,
            reduce_hallucinations: reduceHallucinations,
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
    taskTypeSelector={
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        {/* Dropdown */}
        <div className="flex-1">
          <label
            htmlFor="task-type"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Choose task type:
          </label>
          <select
            id="task-type"
            value={taskType}
            onChange={handleTaskTypeChange}
            className="border border-gray-300 rounded-md p-2 text-sm w-full"
          >
            <option value="abstract">🧠 Abstract Problem Solver</option>
            <option value="functional">📈 Functional Problem Solver (ODEs, equations, integrals...)</option>
            <option value="lesson">📚 Lesson Explainer</option>
          </select>
        </div>

        {/* Toggle */}
        {["abstract", "functional"].includes(taskType) && (
          <div className="flex items-center mt-2 md:mt-7">
            <label className="inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={reduceHallucinations}
                onChange={toggleHallucinations}
                className="form-checkbox h-4 w-4 text-blue-600"
              />
              <span className="ml-2 text-sm text-gray-800">Reduce hallucinations</span>
            </label>
          </div>
        )}
      </div>
    }
  />
  </div>
  );
}