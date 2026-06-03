"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { VideoCard } from "@/components/dashboard/video-card";
import { ChatPanel } from "@/components/chat/chat-panel";
import { ErrorAlert } from "@/components/shared/error-alert";
import { api } from "@/lib/api-client";
import { loadComparison, saveComparison } from "@/lib/storage";
import type { ComparisonState } from "@/lib/types";

function DashboardContent() {
  const searchParams = useSearchParams();
  const creatorIdParam = searchParams.get("creatorId");

  const [comparison, setComparison] = useState<ComparisonState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);

      const stored = loadComparison();
      if (stored && (!creatorIdParam || stored.creatorId === creatorIdParam)) {
        setComparison(stored);
        setIsLoading(false);
        return;
      }

      if (!creatorIdParam) {
        setError("No comparison found. Analyze videos from the homepage first.");
        setIsLoading(false);
        return;
      }

      setError("Session expired. Please run a new comparison from the homepage.");
      setIsLoading(false);
    }

    void load();
  }, [creatorIdParam]);

  const creatorId = comparison?.creatorId;
  const sessionId = comparison?.sessionId;

  useEffect(() => {
    if (!creatorId || sessionId) return;

    const id = creatorId;

    async function initSession() {
      try {
        const session = await api.createChatSession(id, "Shorts vs Reels Chat");
        setComparison((prev) => {
          if (!prev) return prev;
          const next = { ...prev, sessionId: session.id };
          saveComparison(next);
          return next;
        });
      } catch {
        // Chat still works; session created on first message
      }
    }

    void initSession();
  }, [creatorId, sessionId]);

  useEffect(() => {
    if (comparison) saveComparison(comparison);
  }, [comparison]);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error || !comparison) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16">
        <ErrorAlert message={error ?? "Comparison data unavailable"} />
        <Button asChild className="mt-6 w-full" variant="outline">
          <Link href="/">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to home
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Comparison Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Side-by-side metrics and grounded AI chat for this pair.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/">
            <ArrowLeft className="mr-2 h-4 w-4" />
            New comparison
          </Link>
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <VideoCard
          platform="youtube"
          url={comparison.youtubeUrl}
          data={comparison.youtube}
        />
        <VideoCard
          platform="instagram"
          url={comparison.instagramUrl}
          data={comparison.instagram}
        />
      </div>

      <ChatPanel
        creatorId={comparison.creatorId}
        sessionId={comparison.sessionId}
      />
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6">
      <Skeleton className="h-10 w-64" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-96 rounded-xl" />
        <Skeleton className="h-96 rounded-xl" />
      </div>
      <Skeleton className="h-[480px] rounded-xl" />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <DashboardContent />
    </Suspense>
  );
}
