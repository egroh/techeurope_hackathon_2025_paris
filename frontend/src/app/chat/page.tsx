"use client";

import {useEffect, useState, useRef, ChangeEvent} from "react";
import { v4 as uuidv4 } from "uuid";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Upload, Youtube } from "lucide-react";
import { OpenAIChatMessage, OCRResponse, YouTubeSearchResponseData, YouTubeVideo } from "@/lib/apiTypes";
import { Chat } from "@/components/ChatCards";
import {useToast} from "@/hooks/use-toast";

const WS_URL =
  process.env.NEXT_PUBLIC_WS_BACKEND_URL || "ws://localhost:8000/api/chat";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BACKEND_URL || "http://localhost:8000/api";

export default function ChatPage() {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [messages, setMessages] = useState<Array<OpenAIChatMessage>>([]);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("connecting");
  const currentConversationId = useRef<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null); // For OCR
  const [isUploading, setIsUploading] = useState(false); // For OCR
  const [isSearchingYouTube, setIsSearchingYouTube] = useState(false); // For YouTube
  const { toast } = useToast();

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
              const existingMsgIndex = prevMessages.findIndex(msg => msg.id === data.message_id);

              if (data.stream_event === "start") {
                // If message already exists (e.g. due to rapid events), update it, else add new
                if (existingMsgIndex > -1) {
                    return prevMessages.map(msg => msg.id === data.message_id ? {
                        ...msg, // Keep existing content if any
                        ...data, // Spread new data (includes content, isThinking from backend)
                        id: data.message_id, // Ensure ID is from stream
                        isStreaming: true,
                        // isThinking should come from data if backend sends it
                    } : msg);
                }
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
                        isStreaming: true,
                        // Persist isThinking state or update if backend sends it with chunk
                        isThinking: data.isThinkingProcess !== undefined ? data.isThinkingProcess : msg.isThinkingProcess,
                      }
                    : msg
                );
              } else if (data.stream_event === "end") {
                return prevMessages.map((msg) =>
                  msg.id === data.message_id
                    ? {
                        ...msg,
                        // Append final chunk of content if present in 'end' event
                        content: data.content ? (msg.content || "") + data.content : msg.content,
                        isStreaming: false,
                        isThinking: false, // Explicitly set isThinking to false
                      }
                    : msg
                );
              }
            }
            // For non-streamed messages or other types
            // Ensure 'isThinking' from 'data' is included if applicable
            const newMsgId = data.id || data.message_id || uuidv4();
            // Avoid adding duplicate non-streaming messages if they somehow get resent
            if (prevMessages.find(msg => msg.id === newMsgId && !data.stream_event)) {
                return prevMessages;
            }
            return [...prevMessages, { ...data, id: newMsgId }];
          });
        } catch (error) {
          console.error("[ChatPage] Error parsing WebSocket message:", error, event.data);
          setMessages((prev) => [
            ...prev,
            { // Ensure this error message conforms to OpenAIChatMessage structure
              id: uuidv4(),
              type: "error",
              content: "Error processing message from server.",
              conversation_id: currentConversationId.current || "unknown",
              // Add other required fields for OpenAIChatMessage if any, with default/null values
              isStreaming: false,
              isThinking: false,
            } as OpenAIChatMessage, // Explicit cast
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
      const convId = currentConversationId.current || uuidv4(); // Generate if not exists
      if (!currentConversationId.current) {
        currentConversationId.current = convId;
      }

      const userMessage: OpenAIChatMessage = {
        id: uuidv4(), // Client-side unique ID for this message
        type: "human",
        content: messageContent,
        conversation_id: convId,
        // Initialize other OpenAIChatMessage fields to default/null if necessary
        isStreaming: false,
        isThinkingProcess: null, // Not applicable for human messages
        // tool_calls: undefined, tool_call_id: undefined, message_id: undefined, stream_event: undefined
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
          isStreaming: false,
          isThinking: false,
        } as OpenAIChatMessage, // Explicit cast
      ]);
    }
  };

  // --- OCR and YouTube handlers (from previous response, ensure they use OpenAIChatMessage) ---
  const handleFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    toast({ title: "Uploading...", description: `Processing ${file.name}` });
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch(`${API_BASE_URL}/support/ocr/parse-document`, {
        method: "POST", body: formData,
      });
      if (!response.ok) { /* ... error handling ... */ throw new Error(`HTTP error! ${response.status}`); }
      const result = (await response.json()) as OCRResponse;
      const ocrText = result.pages.join("\n\n---\n\n");
      const aiMessage: OpenAIChatMessage = { // Using OpenAIChatMessage
        id: uuidv4(), type: "ai", content: `Document "${file.name}" processed:\n\n${ocrText}`,
        conversation_id: currentConversationId.current || uuidv4(),
        isStreaming: false, isThinkingProcess: false,
      };
      setMessages((prev) => [...prev, aiMessage]);
      toast({ title: "Success", description: "Document processed." });
    } catch (error: any) { /* ... error handling ... */ }
    finally { setIsUploading(false); if (fileInputRef.current) fileInputRef.current.value = ""; }
  };

  const handleYouTubeSearch = async () => {
    const lastUserMessage = messages.filter(m => m.type === 'human').pop()?.content;
    const topicsToSearch = lastUserMessage ? [lastUserMessage.substring(0, 100)] : ["calculus basics"];
    if (topicsToSearch.length === 0) { /* ... */ return; }
    setIsSearchingYouTube(true);
    toast({ title: "Searching YouTube...", description: `For: ${topicsToSearch.join(", ")}` });
    try {
      const response = await fetch(`${API_BASE_URL}/support/youtube/search-by-topics`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topics: topicsToSearch, videos_per_topic: 2 }),
      });
      if (!response.ok) { /* ... error handling ... */ throw new Error(`HTTP error! ${response.status}`); }
      const result = (await response.json()) as YouTubeSearchResponseData;
      let youtubeResultsContent = "YouTube Video Recommendations:\n\n";
      // ... (formatting logic for youtubeResultsContent) ...
      if (Object.keys(result.results).length === 0) {
        youtubeResultsContent += "No videos found.";
      } else {
        for (const topic in result.results) {
          youtubeResultsContent += `**Topic: ${topic}**\n`;
          result.results[topic].forEach((video: YouTubeVideo, index: number) => {
            youtubeResultsContent += `${index + 1}. [${video.title || 'N/A'}](${video.url})\n   Channel: ${video.channel || 'N/A'}\n`;
          });
          youtubeResultsContent += "\n";
        }
      }
      const aiMessage: OpenAIChatMessage = { // Using OpenAIChatMessage
        id: uuidv4(), type: "ai", content: youtubeResultsContent,
        conversation_id: currentConversationId.current || uuidv4(),
        isStreaming: false, isThinkingProcess: false,
      };
      setMessages((prev) => [...prev, aiMessage]);
      toast({ title: "YouTube Search Complete" });
    } catch (error: any) { /* ... error handling ... */ }
    finally { setIsSearchingYouTube(false); }
  };
  // --- End OCR and YouTube handlers ---


  return (
    <div className="flex flex-col h-screen bg-muted/20 dark:bg-black"> {/* Adjusted background */}
      <div className="p-3 border-b bg-background shadow-sm sticky top-0 z-20">
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
            className="border border-input bg-background hover:bg-accent hover:text-accent-foreground rounded-md p-2 text-xs w-full h-9" // Adjusted styling
          >
            <option value="abstract">🧠 Abstract Solver</option>
            <option value="functional">📈 Functional Solver</option>
            <option value="lesson">📚 Lesson Explainer</option>
          </select>
        </div>
        {/* Action Buttons */}
        <div className="flex items-center space-x-2 flex-shrink-0"> {/* Buttons don't grow */}
          <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} disabled={isUploading} className="text-xs h-9">
            <Upload className="mr-1.5 h-3.5 w-3.5" /> {isUploading ? "Uploading..." : "OCR"}
          </Button>
          <Input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.png,.jpg,.jpeg" />
          <Button variant="outline" size="sm" onClick={handleYouTubeSearch} disabled={isSearchingYouTube} className="text-xs h-9">
            <Youtube className="mr-1.5 h-3.5 w-3.5" /> {isSearchingYouTube ? "Searching..." : "Videos"}
          </Button>
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