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

      const eventTypes: StreamEventType[] = [
        "status",
        "token",
        "citation",
        "done",
        "error",
      ];

      for (const eventType of eventTypes) {
        source.addEventListener(eventType, (event) => {
          try {
            const data = JSON.parse((event as MessageEvent).data) as StreamEventPayload;
            switch (eventType) {
              case "status":
                handlers.onStatus?.(data);
                break;
              case "token":
                handlers.onToken?.(String(data.delta ?? ""));
                break;
              case "citation": {
                const citation = data as unknown as Citation;
                handlers.onCitation?.(citation);
                break;
              }
              case "done":
                handlers.onDone?.(data);
                close();
                break;
              case "error":
                handlers.onError?.(String(data.message ?? "Stream error"));
                close();
                break;
            }
          } catch {
            handlers.onError?.("Failed to parse stream event");
          }
        });
      }

      source.onerror = () => {
        handlers.onError?.("Connection to stream lost");
        close();
      };
    },
    [close],
  );

  return { connect, close };
}
