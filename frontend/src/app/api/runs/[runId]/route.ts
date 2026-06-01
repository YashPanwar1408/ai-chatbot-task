import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/server-api";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  try {
    const { runId } = await params;
    const response = await backendFetch(`/runs/${runId}`);
    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail ?? "Run not found" },
        { status: response.status },
      );
    }
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Backend unreachable";
    return NextResponse.json({ detail: message }, { status: 502 });
  }
}
