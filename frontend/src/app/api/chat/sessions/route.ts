import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/server-api";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const response = await backendFetch("/chat/sessions", {
      method: "POST",
      body: JSON.stringify(body),
    });

    const raw = await response.text();
    let data: { detail?: string } = {};
    try {
      data = raw ? (JSON.parse(raw) as { detail?: string }) : {};
    } catch {
      return NextResponse.json(
        { detail: raw.slice(0, 200) || "Invalid backend response" },
        { status: response.status || 502 },
      );
    }
    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail ?? "Failed to create session" },
        { status: response.status },
      );
    }

    return NextResponse.json(JSON.parse(raw), { status: 201 });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Backend unreachable";
    return NextResponse.json({ detail: message }, { status: 502 });
  }
}
