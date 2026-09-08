import { useState, useEffect, useCallback, useRef } from "react";
import { AuthManager } from "../auth/token";

export interface SSEMessage {
  event: string;
  data: any;
  timestamp: string;
}

export function useSSE(endpoint: string | null) {
  const [messages, setMessages] = useState<SSEMessage[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  useEffect(() => {
    if (!endpoint) {
      setIsConnected(false);
      return;
    }

    const abortController = new AbortController();
    let isCancelled = false;

    async function startStream() {
      try {
        const token = AuthManager.getToken();
        const headers: Record<string, string> = {
          Accept: "text/event-stream",
        };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const response = await fetch(endpoint!, {
          headers,
          signal: abortController.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(`SSE stream connection failed with HTTP ${response.status}`);
        }

        setIsConnected(true);
        setError(null);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!isCancelled) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            if (!part.trim()) continue;
            let eventType = "message";
            let dataStr = "";

            for (const line of part.split("\n")) {
              if (line.startsWith("event:")) {
                eventType = line.replace("event:", "").trim();
              } else if (line.startsWith("data:")) {
                dataStr = line.replace("data:", "").trim();
              }
            }

            if (dataStr) {
              try {
                const parsed = JSON.parse(dataStr);
                setMessages((prev) => [
                  ...prev,
                  {
                    event: eventType,
                    data: parsed,
                    timestamp: new Date().toISOString(),
                  },
                ]);
              } catch {
                setMessages((prev) => [
                  ...prev,
                  {
                    event: eventType,
                    data: dataStr,
                    timestamp: new Date().toISOString(),
                  },
                ]);
              }
            }
          }
        }
      } catch (err: any) {
        if (!isCancelled && err?.name !== "AbortError") {
          setIsConnected(false);
          setError("SSE connection closed or lost.");
        }
      }
    }

    startStream();

    return () => {
      isCancelled = true;
      abortController.abort();
      setIsConnected(false);
    };
  }, [endpoint]);

  return { messages, isConnected, error, clearMessages };
}
