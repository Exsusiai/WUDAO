import { BookOpen } from "lucide-react";

export default function JournalPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
      <BookOpen className="h-8 w-8 text-muted-foreground/50" strokeWidth={1} />
      <div>
        <h1 className="text-lg font-light tracking-wide">Journal</h1>
        <p className="mt-1 text-xs font-light text-muted-foreground">
          交易记录与复盘笔记将在此呈现
        </p>
      </div>
    </div>
  );
}
