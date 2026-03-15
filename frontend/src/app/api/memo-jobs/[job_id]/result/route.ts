import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function GET(_req: Request, { params }: { params: Promise<{ job_id: string }> }) {
  try {
    const { job_id } = await params;
    const res = await fetch(`${BACKEND_URL}/api/memo-jobs/${job_id}/result`, { cache: "no-store" });
    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 502 });
  }
}
