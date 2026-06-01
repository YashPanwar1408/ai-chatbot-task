export type AnalysisRunStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed";

export interface VideoPlatformSummary {
  content_id: string;
  creator: string;
  views: number | null;
  likes: number | null;
  comments: number | null;
  upload_date: string | null;
  hashtags: string[];
  engagement_rate: number;
  transcript_preview?: string | null;
}

export interface CompareUrlsResponse {
  creator_id: string;
  youtube: VideoPlatformSummary;
  instagram: VideoPlatformSummary;
  run_id?: string | null;
  run_status?: AnalysisRunStatus | null;
}

export interface CompareUrlsRequest {
  youtube_url: string;
  instagram_url: string;
  display_name?: string;
  query?: string;
}

export interface ChatSessionResponse {
  id: string;
  creator_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageResponse {
  run_id: string;
  status: AnalysisRunStatus;
}

export interface Citation {
  rank?: number;
  chunk_id?: string;
  content_item_id?: string;
  score?: number;
  platform?: string;
  url?: string;
  title?: string;
  text_preview?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  status?: "streaming" | "done" | "error";
}

export interface ComparisonState {
  creatorId: string;
  youtubeUrl: string;
  instagramUrl: string;
  youtube: VideoPlatformSummary;
  instagram: VideoPlatformSummary;
  sessionId?: string;
}

export const COMPARISON_STORAGE_KEY = "shorts-reels-comparison";

export type StreamEventType =
  | "status"
  | "token"
  | "citation"
  | "metric"
  | "done"
  | "error";

export interface StreamEventPayload {
  phase?: string;
  delta?: string;
  message?: string;
  run_id?: string;
  status?: string;
  [key: string]: unknown;
}
