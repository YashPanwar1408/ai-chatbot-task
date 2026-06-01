import type {
  ChatMessageResponse,
  ChatSessionResponse,
  CompareUrlsRequest,
  CompareUrlsResponse,
} from "@/lib/types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail ?? body.message ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const message = await parseError(response);
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

export const api = {
  compareUrls(body: CompareUrlsRequest): Promise<CompareUrlsResponse> {
    return request<CompareUrlsResponse>("/api/compare/urls", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  createChatSession(creatorId: string, title?: string): Promise<ChatSessionResponse> {
    return request<ChatSessionResponse>("/api/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ creator_id: creatorId, title }),
    });
  },

  sendChatMessage(
    sessionId: string,
    message: string,
  ): Promise<ChatMessageResponse> {
    return request<ChatMessageResponse>(`/api/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  },

  getRun(runId: string) {
    return request<Record<string, unknown>>(`/api/runs/${runId}`);
  },
};

export function streamRunUrl(runId: string): string {
  return `/api/runs/${runId}/stream`;
}
