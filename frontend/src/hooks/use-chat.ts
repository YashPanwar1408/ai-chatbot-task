"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import { loadChatMemory, saveChatMemory } from "@/lib/storage";
import type { ChatMessage, Citation } from "@/lib/types";
import { useSSE } from "@/hooks/use-sse";

function isPhasePlaceholder(text: string): boolean {
  return text.startsWith("_") && text.endsWith("_") && text.includes("...");
}

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
        let hasReceivedContent = false;

        const hydrateFromRun = async (): Promise<boolean> => {
          try {
            const run = (await api.getRun(run_id)) as Record<string, unknown>;
            const status = typeof run.status === "string" ? run.status : undefined;
            const errorText = typeof run.error === "string" ? run.error : undefined;
            const resultSummary =
              run.result_summary && typeof run.result_summary === "object"
                ? (run.result_summary as Record<string, unknown>)
                : undefined;
            const answer =
              resultSummary && typeof resultSummary.answer === "string"
                ? resultSummary.answer
                : undefined;
            const summaryCitations =
              resultSummary && Array.isArray(resultSummary.citations)
                ? (resultSummary.citations as Citation[])
                : undefined;

            if (status === "failed") {
              setError(errorText ?? "Run failed");
              workingMessages = workingMessages.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      content:
                        !msg.content || isPhasePlaceholder(msg.content)
                          ? "Failed to generate a response."
                          : msg.content,
                      status: "error" as const,
                    }
                  : msg,
              );
              persistMessages([...workingMessages]);
              return true;
            }

            if (status === "completed") {
              workingMessages = workingMessages.map((msg) => {
                if (msg.id !== assistantId) return msg;
                const next: ChatMessage = {
                  ...msg,
                  status: "done" as const,
                };

                if (!next.content || isPhasePlaceholder(next.content)) {
                  if (answer) next.content = answer;
                }

                if (
                  (!next.citations || next.citations.length === 0) &&
                  summaryCitations &&
                  summaryCitations.length
                ) {
                  next.citations = summaryCitations;
                }

                return next;
              });
              persistMessages([...workingMessages]);
              setIsLoading(false);
              return true;
            }

            return false;
          } catch {
            return false;
          }
        };

        const pollRunUntilTerminal = async (): Promise<boolean> => {
          const maxAttempts = 30;
          for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
            // eslint-disable-next-line no-await-in-loop
            const done = await hydrateFromRun();
            if (done) return true;
            // eslint-disable-next-line no-await-in-loop
            await new Promise((resolve) => setTimeout(resolve, 1000));
          }
          return false;
        };

        void pollRunUntilTerminal();

        connect(run_id, {
          onStatus: (data) => {
            if (data.phase && !hasReceivedContent) {
              workingMessages = workingMessages.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      content:
                        !message.content || isPhasePlaceholder(message.content)
                          ? `_${data.phase}..._`
                          : message.content,
                    }
                  : message,
              );
              persistMessages([...workingMessages]);
            }
          },
          onToken: (delta) => {
            if (!delta) return;
            hasReceivedContent = true;
            workingMessages = workingMessages.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content:
                      !message.content || isPhasePlaceholder(message.content)
                        ? delta
                        : message.content + delta,
                  }
                : message,
            );
            persistMessages([...workingMessages]);
          },
          onCitation: (citation) => {
            hasReceivedContent = true;
            citations.push(citation);
            workingMessages = workingMessages.map((message) =>
              message.id === assistantId
                ? { ...message, citations: [...citations] }
                : message,
            );
            persistMessages([...workingMessages]);
          },
          onDone: (data) => {
            void (async () => {
              const streamedAnswer =
                typeof data.answer === "string" ? data.answer : undefined;
              if (streamedAnswer) {
                workingMessages = workingMessages.map((message) =>
                  message.id === assistantId
                    ? {
                        ...message,
                        content: streamedAnswer,
                        status: "done" as const,
                      }
                    : message,
                );
                persistMessages([...workingMessages]);
              } else {
                await hydrateFromRun();
                workingMessages = workingMessages.map((message) =>
                  message.id === assistantId
                    ? { ...message, status: "done" as const }
                    : message,
                );
                persistMessages([...workingMessages]);
              }
              setIsLoading(false);
            })();
          },
          onError: (message) => {
            void (async () => {
              const recovered = await pollRunUntilTerminal();
              if (recovered) {
                setIsLoading(false);
                return;
              }

              setError(message);
              workingMessages = workingMessages.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      content:
                        !msg.content || isPhasePlaceholder(msg.content)
                          ? "Failed to generate a response."
                          : msg.content,
                      status: "error" as const,
                    }
                  : msg,
              );
              persistMessages([...workingMessages]);
              setIsLoading(false);
            })();
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
