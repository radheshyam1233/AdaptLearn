// src/useLiveFeed.js
// A custom React hook: opens the WebSocket, collects live events,
// and reconnects automatically if the connection drops.

import { useEffect, useRef, useState } from "react";
import { API_URL, getToken } from "./api";

export function useLiveFeed(onEvent) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);
  // Keep the ref pointing at the latest callback (updated after each render)
  useEffect(() => {
    onEventRef.current = onEvent;
  });

  useEffect(() => {
    let ws;
    let retryTimer;
    let stopped = false;

    function connect() {
      // http://... -> ws://...   https://... -> wss://...
      const url = `${API_URL.replace(/^http/, "ws")}/ws/dashboard?token=${getToken()}`;
      ws = new WebSocket(url);
      ws.onopen = () => setConnected(true);
      ws.onmessage = (msg) => {
        const event = JSON.parse(msg.data);
        setEvents((prev) => [event, ...prev].slice(0, 30));   // keep the newest 30
        onEventRef.current?.(event);
      };
      ws.onclose = () => {
        setConnected(false);
        if (!stopped) retryTimer = setTimeout(connect, 3000);  // try again in 3 s
      };
    }

    connect();
    // Cleanup when the page closes: stop retrying and close the socket
    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      ws?.close();
    };
  }, []);

  return { events, connected };
}
