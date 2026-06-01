"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Instagram, Loader2, Youtube } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorAlert } from "@/components/shared/error-alert";
import { api, ApiError } from "@/lib/api-client";
import { saveComparison } from "@/lib/storage";

export function UrlForm() {
  const router = useRouter();
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [instagramUrl, setInstagramUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const result = await api.compareUrls({
        youtube_url: youtubeUrl.trim(),
        instagram_url: instagramUrl.trim(),
      });

      saveComparison({
        creatorId: result.creator_id,
        youtubeUrl: youtubeUrl.trim(),
        instagramUrl: instagramUrl.trim(),
        youtube: result.youtube,
        instagram: result.instagram,
      });

      router.push(`/dashboard?creatorId=${result.creator_id}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Failed to analyze videos. Check URLs and backend connection.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Card className="mx-auto w-full max-w-2xl border-border/60 shadow-lg">
      <CardHeader>
        <CardTitle className="text-2xl">Compare a Short and a Reel</CardTitle>
        <CardDescription>
          Paste public URLs to extract metrics, index transcripts, and chat with grounded
          citations.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="youtube" className="flex items-center gap-2">
              <Youtube className="h-4 w-4 text-youtube" />
              YouTube Short URL
            </Label>
            <Input
              id="youtube"
              type="url"
              placeholder="https://www.youtube.com/shorts/..."
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="instagram" className="flex items-center gap-2">
              <Instagram className="h-4 w-4 text-instagram" />
              Instagram Reel URL
            </Label>
            <Input
              id="instagram"
              type="url"
              placeholder="https://www.instagram.com/reel/..."
              value={instagramUrl}
              onChange={(e) => setInstagramUrl(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          {error && <ErrorAlert message={error} />}

          <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Extracting &amp; indexing...
              </>
            ) : (
              <>
                Analyze videos
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>

          {isLoading && (
            <p className="text-center text-xs text-muted-foreground">
              This may take a minute while transcripts are fetched and embeddings are
              generated.
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
