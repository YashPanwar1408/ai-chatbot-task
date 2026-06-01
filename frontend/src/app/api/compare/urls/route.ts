import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/server-api";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const response = await backendFetch("/compare/urls", {
      method: "POST",
      body: JSON.stringify(body),
    });

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail ?? "Compare failed" },
        { status: response.status },
      );
    }

    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Backend unreachable";
    return NextResponse.json({ detail: message }, { status: 502 });
  }
}
