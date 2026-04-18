"use client";

import { LayoutDashboard } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-lg font-light tracking-wide">Dashboard</h1>
        <p className="mt-1 text-xs font-light text-muted-foreground">
          账户总览、持仓状态与待处理事项
        </p>
      </div>

      <div className="rounded-md border bg-card p-6">
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <LayoutDashboard
            className="h-8 w-8 text-muted-foreground/50"
            strokeWidth={1}
          />
          <p className="text-xs font-light text-muted-foreground">
            功能模块将随开发进度逐步上线
          </p>
        </div>
      </div>
    </div>
  );
}
