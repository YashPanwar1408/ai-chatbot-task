"use client";

import { useState } from "react";
import { Send, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ErrorAlert } from "@/components/shared/error-alert";
import { MessageList } from "@/components/chat/message-list";
import { useChat } from "@/hooks/use-chat";

interface ChatPanelProps {
  creatorId: string;
  sessionId?: string;
}

export function ChatPanel({ creatorId, sessionId }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const { messages, isLoading, isInitializing, error, sendMessage, clearChat } =
    useChat(creatorId, sessionId ?? null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
    await sendMessage(text);
  }

  return (
    <Card className="flex h-[min(720px,calc(100vh-12rem))] flex-col">
      <CardHeader className="shrink-0 border-b pb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>AI Compare Chat</CardTitle>
            <CardDescription>
              Streaming RAG answers with citations and conversation memory.
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={clearChat}
            disabled={isLoading || !messages.length}
            title="Clear local chat history"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex min-h-0 flex-1 flex-col gap-4 pt-4">
        <div className="min-h-0 flex-1">
          <MessageList messages={messages} />
        </div>

        {error && <ErrorAlert message={error} />}

        <form onSubmit={handleSubmit} className="flex shrink-0 gap-2">
          <Textarea
            placeholder="e.g. Which hook is stronger? Compare engagement drivers."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading || isInitializing}
            className="min-h-[60px] resize-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSubmit(e);
              }
            }}
          />
          <Button
            type="submit"
            size="icon"
            className="h-[60px] w-[60px] shrink-0"
            disabled={isLoading || isInitializing || !input.trim()}
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
