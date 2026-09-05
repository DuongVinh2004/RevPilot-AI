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

    // Set authorization header in query param or rely on proxy/cookie if standard EventSource
    const token = AuthManager.getToken();
    const url = token ? `${endpoint}?token=${encodeURIComponent(token)}` : endpoint;

    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    es.onerror = (err) => {
      setIsConnected(false);
      setError("SSE connection closed or lost. Retrying...");
    };

    // Generic and specific event listeners
    const handleEvent = (event: MessageEvent, eventType: string) => {
      try {
        const parsed = JSON.parse(event.data);
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
            data: event.data,
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    };

    es.onmessage = (e) => handleEvent(e, "message");
    es.addEventListener("connected", (e: any) => handleEvent(e, "connected"));
    es.addEventListener("node_progress", (e: any) => handleEvent(e, "node_progress"));
    es.addEventListener("completed", (e: any) => handleEvent(e, "completed"));

    return () => {
      es.close();
      setIsConnected(false);
    };
  }, [endpoint]);

  return { messages, isConnected, error, clearMessages };
}
