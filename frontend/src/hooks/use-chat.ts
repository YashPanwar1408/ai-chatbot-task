"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import { loadChatMemory, saveChatMemory } from "@/lib/storage";
import type { ChatMessage, Citation } from "@/lib/types";
import { useSSE } from "@/hooks/use-sse";

function newMessageId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function useChat(creatorId: string | null, sessionId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(sessionId);
  const { connect, close } = useSSE();

  useEffect(() => {
    if (!creatorId) return;
    setMessages(loadChatMemory(creatorId));
  }, [creatorId]);

  useEffect(() => {
    if (sessionId) setActiveSessionId(sessionId);
  }, [sessionId]);

  const persistMessages = useCallback(
    (next: ChatMessage[]) => {
      if (creatorId) saveChatMemory(creatorId, next);
      setMessages(next);
    },
    [creatorId],
  );

  const ensureSession = useCallback(async () => {
    if (activeSessionId) return activeSessionId;
    if (!creatorId) throw new Error("Creator id is required");

    setIsInitializing(true);
    setError(null);
    try {
      const session = await api.createChatSession(
        creatorId,
        "Shorts vs Reels Chat",
      );
      setActiveSessionId(session.id);
      return session.id;
    } finally {
      setIsInitializing(false);
    }
  }, [activeSessionId, creatorId]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!creatorId || !text.trim()) return;

      setIsLoading(true);
      setError(null);
      close();

      const userMessage: ChatMessage = {
        id: newMessageId(),
        role: "user",
        content: text.trim(),
        status: "done",
      };

      const assistantId = newMessageId();
      const assistantPlaceholder: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        citations: [],
        status: "streaming",
      };

      let workingMessages = [...messages, userMessage, assistantPlaceholder];
      persistMessages(workingMessages);

      try {
        const sid = await ensureSession();
        const { run_id } = await api.sendChatMessage(sid, text.trim());

        const citations: Citation[] = [];

        connect(run_id, {
          onStatus: (data) => {
            if (data.phase) {
              workingMessages = workingMessages.map((message) =>
                message.id === assistantId
                  ? { ...message, content: message.content || `_${data.phase}..._` }
                  : message,
              );
              persistMessages([...workingMessages]);
            }
          },
          onToken: (delta) => {
            workingMessages = workingMessages.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content:
                      message.content.startsWith("_") && message.content.endsWith("_")
                        ? delta
                        : message.content + delta,
                  }
                : message,
            );
            persistMessages([...workingMessages]);
          },
          onCitation: (citation) => {
            citations.push(citation);
            workingMessages = workingMessages.map((message) =>
              message.id === assistantId
                ? { ...message, citations: [...citations] }
                : message,
            );
            persistMessages([...workingMessages]);
          },
          onDone: () => {
            workingMessages = workingMessages.map((message) =>
              message.id === assistantId
                ? { ...message, status: "done" as const }
                : message,
            );
            persistMessages([...workingMessages]);
            setIsLoading(false);
          },
          onError: (message) => {
            setError(message);
            workingMessages = workingMessages.map((msg) =>
              msg.id === assistantId
                ? {
                    ...msg,
                    content: msg.content || "Failed to generate a response.",
                    status: "error" as const,
                  }
                : msg,
            );
            persistMessages([...workingMessages]);
            setIsLoading(false);
          },
        });
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : "Failed to send message";
        setError(message);
        persistMessages(messages.filter((m) => m.id !== assistantId));
        setIsLoading(false);
      }
    },
    [creatorId, messages, persistMessages, ensureSession, connect, close],
  );

  const clearChat = useCallback(() => {
    close();
    persistMessages([]);
    setError(null);
  }, [close, persistMessages]);

  return {
    messages,
    isLoading,
    isInitializing,
    error,
    sessionId: activeSessionId,
    sendMessage,
    clearChat,
    ensureSession,
  };
}
