import { Calendar, Eye, Heart, MessageCircle, TrendingUp, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatDate, formatNumber, formatPercent } from "@/lib/utils";
import type { VideoPlatformSummary } from "@/lib/types";

interface VideoCardProps {
  platform: "youtube" | "instagram";
  url: string;
  data: VideoPlatformSummary;
}

const platformConfig = {
  youtube: {
    label: "YouTube Short",
    variant: "youtube" as const,
    accent: "border-t-4 border-t-youtube",
  },
  instagram: {
    label: "Instagram Reel",
    variant: "instagram" as const,
    accent: "border-t-4 border-t-instagram",
  },
};

export function VideoCard({ platform, url, data }: VideoCardProps) {
  const config = platformConfig[platform];

  return (
    <Card className={`flex flex-col ${config.accent}`}>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <Badge variant={config.variant}>{config.label}</Badge>
          <Badge variant="outline" className="gap-1 font-mono text-xs">
            <TrendingUp className="h-3 w-3" />
            {formatPercent(data.engagement_rate)}
          </Badge>
        </div>
        <CardTitle className="line-clamp-2 text-lg leading-snug">
          {data.creator}
        </CardTitle>
        <CardDescription className="line-clamp-1 break-all text-xs">
          <a href={url} target="_blank" rel="noopener noreferrer" className="hover:underline">
            {url}
          </a>
        </CardDescription>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-4">
        <div className="grid grid-cols-3 gap-3">
          <Metric icon={Eye} label="Views" value={formatNumber(data.views)} />
          <Metric icon={Heart} label="Likes" value={formatNumber(data.likes)} />
          <Metric
            icon={MessageCircle}
            label="Comments"
            value={formatNumber(data.comments)}
          />
        </div>

        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <User className="h-4 w-4 shrink-0" />
          <span className="truncate">{data.creator}</span>
        </div>

        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar className="h-4 w-4 shrink-0" />
          <span>{formatDate(data.upload_date)}</span>
        </div>

        {data.hashtags.length > 0 && (
          <>
            <Separator />
            <div className="flex flex-wrap gap-1.5">
              {data.hashtags.slice(0, 8).map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs font-normal">
                  {tag}
                </Badge>
              ))}
              {data.hashtags.length > 8 && (
                <Badge variant="outline" className="text-xs">
                  +{data.hashtags.length - 8}
                </Badge>
              )}
            </div>
          </>
        )}

        {data.transcript_preview && (
          <>
            <Separator />
            <p className="line-clamp-4 text-xs leading-relaxed text-muted-foreground">
              {data.transcript_preview}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg bg-muted/50 p-3 text-center">
      <Icon className="mx-auto mb-1 h-4 w-4 text-muted-foreground" />
      <p className="text-lg font-semibold tabular-nums">{value}</p>
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
    </div>
  );
}
