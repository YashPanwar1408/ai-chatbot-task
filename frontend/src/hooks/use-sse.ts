"use client";

import { useCallback, useEffect, useRef } from "react";
import type { Citation, StreamEventPayload, StreamEventType } from "@/lib/types";
import { streamRunUrl } from "@/lib/api-client";

export interface UseSSEHandlers {
  onStatus?: (data: StreamEventPayload) => void;
  onToken?: (delta: string) => void;
  onCitation?: (citation: Citation) => void;
  onDone?: (data: StreamEventPayload) => void;
  onError?: (message: string) => void;
}

export function useSSE() {
  const sourceRef = useRef<EventSource | null>(null);

  const close = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
  }, []);

  useEffect(() => () => close(), [close]);

  const connect = useCallback(
    (runId: string, handlers: UseSSEHandlers) => {
      close();
      const source = new EventSource(streamRunUrl(runId));
      sourceRef.current = source;
      let finished = false;

      let receivedContent = false;

      const handlePayload = (eventType: StreamEventType, raw: string) => {
        const data = JSON.parse(raw) as StreamEventPayload;
        switch (eventType) {
          case "status":
            handlers.onStatus?.(data);
            break;
          case "token": {
            const delta = String(data.delta ?? "");
            if (delta) receivedContent = true;
            handlers.onToken?.(delta);
            break;
          }
          case "citation": {
            receivedContent = true;
            handlers.onCitation?.(data as unknown as Citation);
            break;
          }
          case "metric":
            break;
          case "done":
            finished = true;
            handlers.onDone?.(data);
            close();
            break;
          case "error":
            finished = true;
            handlers.onError?.(String(data.message ?? "Stream error"));
            close();
            break;
        }
      };

      const eventTypes: StreamEventType[] = [
        "status",
        "token",
        "citation",
        "metric",
        "done",
        "error",
      ];

      for (const eventType of eventTypes) {
        source.addEventListener(eventType, (event) => {
          try {
            if (!(event instanceof MessageEvent) || typeof event.data !== "string") {
              return;
            }
            handlePayload(eventType, event.data);
          } catch {
            if (!finished) {
              finished = true;
              handlers.onError?.("Failed to parse stream event");
              close();
            }
          }
        });
      }

      source.onerror = () => {
        if (finished) return;
        finished = true;
        if (!receivedContent) {
          handlers.onError?.("Connection to stream lost");
        } else {
          handlers.onDone?.({});
        }
        close();
      };
    },
    [close],
  );

  return { connect, close };
}
