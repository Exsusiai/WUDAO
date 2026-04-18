"use client";

import { Badge } from "@/components/ui/badge";

const MODE: "SANDBOX" | "LIVE" = "SANDBOX";

export function TopBar() {
  return (
    <header className="flex h-12 items-center justify-between border-b border-border/50 bg-background px-6">
      <div className="text-xs font-light tracking-[0.15em] text-muted-foreground">
        交易工作台
      </div>

      <div className="flex items-center gap-3">
        <Badge
          variant={MODE === "LIVE" ? "destructive" : "outline"}
          className="rounded-sm px-2 py-0 text-[10px] font-light tracking-[0.2em]"
        >
          {MODE}
        </Badge>
      </div>
    </header>
  );
}
