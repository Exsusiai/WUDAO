import { Route } from "lucide-react";

export default function StrategiesPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
      <Route className="h-8 w-8 text-muted-foreground/50" strokeWidth={1} />
      <div>
        <h1 className="text-lg font-light tracking-wide">Strategies</h1>
        <p className="mt-1 text-xs font-light text-muted-foreground">
          纪律规则与交易策略将在此管理
        </p>
      </div>
    </div>
  );
}
