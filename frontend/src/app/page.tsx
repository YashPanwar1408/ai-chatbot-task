import { Sparkles } from "lucide-react";
import { UrlForm } from "@/components/home/url-form";

export default function HomePage() {
  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-muted via-background to-background" />
      <div className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
        <div className="mb-12 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border bg-background px-4 py-1.5 text-sm text-muted-foreground shadow-sm">
            <Sparkles className="h-4 w-4 text-primary" />
            RAG-powered Shorts vs Reels intelligence
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Compare short-form video performance
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            Extract transcripts and engagement metrics, index content with BGE embeddings,
            and chat with streaming citations.
          </p>
        </div>
        <UrlForm />
      </div>
    </div>
  );
}
