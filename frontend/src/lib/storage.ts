import type { ComparisonState } from "@/lib/types";
import { COMPARISON_STORAGE_KEY } from "@/lib/types";

export function saveComparison(state: ComparisonState): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(COMPARISON_STORAGE_KEY, JSON.stringify(state));
}

export function loadComparison(): ComparisonState | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(COMPARISON_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ComparisonState;
  } catch {
    return null;
  }
}

export function clearComparison(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(COMPARISON_STORAGE_KEY);
}

const CHAT_MEMORY_PREFIX = "shorts-reels-chat:";

export function loadChatMemory(creatorId: string): import("@/lib/types").ChatMessage[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(`${CHAT_MEMORY_PREFIX}${creatorId}`);
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function saveChatMemory(
  creatorId: string,
  messages: import("@/lib/types").ChatMessage[],
): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(`${CHAT_MEMORY_PREFIX}${creatorId}`, JSON.stringify(messages));
}
