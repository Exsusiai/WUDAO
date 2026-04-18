"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Crosshair,
  BookOpen,
  Route,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/trade", label: "Trade", icon: Crosshair },
  { href: "/journal", label: "Journal", icon: BookOpen },
  { href: "/strategies", label: "Strategies", icon: Route },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-56 flex-col border-r border-border/50 bg-sidebar">
      {/* Brand */}
      <div className="flex h-14 items-center border-b border-border/50 px-5">
        <span className="text-base font-light tracking-[0.2em] text-sidebar-foreground">
          悟道
        </span>
        <span className="ml-2 text-xs font-light tracking-widest text-muted-foreground">
          WUDAO
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-0.5">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-sidebar-accent text-sidebar-foreground font-medium"
                      : "text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" strokeWidth={1.5} />
                  <span className="tracking-wide">{label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="border-t border-border/50 px-5 py-3">
        <p className="text-[10px] font-light tracking-wide text-muted-foreground">
          本地模式 · 单用户
        </p>
      </div>
    </aside>
  );
}
