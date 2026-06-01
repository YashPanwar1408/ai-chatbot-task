import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Citation } from "@/lib/types";

export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;

  return (
    <div className="mt-3 space-y-2 rounded-lg border bg-muted/30 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Sources
      </p>
      <ul className="space-y-2">
        {citations.map((citation, index) => (
          <li key={`${citation.chunk_id ?? index}-${citation.rank}`} className="text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="text-[10px]">
                [{citation.rank ?? index + 1}]
              </Badge>
              {citation.platform && (
                <Badge
                  variant={citation.platform === "youtube" ? "youtube" : "instagram"}
                  className="text-[10px]"
                >
                  {citation.platform}
                </Badge>
              )}
              {citation.url && (
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  {citation.title ?? "Source"}
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
            {citation.text_preview && (
              <p className="mt-1 line-clamp-2 text-muted-foreground">
                {citation.text_preview}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
