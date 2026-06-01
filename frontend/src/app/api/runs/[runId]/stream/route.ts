import { getBackendUrl } from "@/lib/server-api";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  const backendUrl = getBackendUrl(`/runs/${runId}/stream`);

  try {
    const response = await fetch(backendUrl, {
      headers: { Accept: "text/event-stream" },
      cache: "no-store",
    });

    if (!response.ok || !response.body) {
      return new Response("Stream unavailable", { status: response.status });
    }

    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch {
    return new Response("Backend unreachable", { status: 502 });
  }
}
