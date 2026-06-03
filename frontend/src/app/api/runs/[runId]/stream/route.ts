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

    // Passthrough without buffering the full body (fixes stuck SSE in Next.js proxy).
    const { readable, writable } = new TransformStream<Uint8Array, Uint8Array>();
    void response.body.pipeTo(writable);

    return new Response(readable, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch {
    return new Response("Backend unreachable", { status: 502 });
  }
}
