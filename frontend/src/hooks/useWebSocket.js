import { useEffect, useRef, useState, useCallback } from "react";

const RECONNECT_INTERVAL = 3000;

export default function useWebSocket(url) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("disconnected"); // connected | disconnected | reconnecting
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("reconnecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        setData(parsed);
      } catch {
        // ignore non-JSON frames
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      wsRef.current = null;
      reconnectTimer.current = setTimeout(connect, RECONNECT_INTERVAL);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { data, status };
}
