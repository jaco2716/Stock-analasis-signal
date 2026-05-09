"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { SIGNAL_COLORS } from "@/lib/constants";
import { formatPercent, formatRelativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Signal } from "@/lib/types";

interface SignalsFeedProps {
  signals: Signal[];
  emptyMessage?: string;
}

export const SignalsFeed = ({
  signals,
  emptyMessage = "No signals yet. Run an analysis to generate signals.",
}: SignalsFeedProps) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  if (signals.length === 0) {
    return (
      <div className="rounded-md border p-6 text-sm text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {signals.map((s) => {
        const colors = SIGNAL_COLORS[s.signal_type];
        const isExpanded = expanded[s.id] ?? false;
        return (
          <Card key={s.id}>
            <CardContent className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <Badge
                    variant="outline"
                    className={cn(colors.bg, colors.text, colors.border)}
                  >
                    {s.signal_type}
                  </Badge>
                  <span className="font-mono font-medium">{s.ticker}</span>
                  <span className="text-sm text-muted-foreground">
                    {formatPercent(s.confidence)} confidence
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {formatRelativeTime(s.generated_at)}
                </span>
              </div>
              <button
                type="button"
                onClick={() =>
                  setExpanded((prev) => ({ ...prev, [s.id]: !isExpanded }))
                }
                className={cn(
                  "mt-3 w-full text-left text-sm leading-relaxed",
                  !isExpanded && "line-clamp-3",
                )}
                aria-expanded={isExpanded}
              >
                {s.reasoning}
              </button>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};
