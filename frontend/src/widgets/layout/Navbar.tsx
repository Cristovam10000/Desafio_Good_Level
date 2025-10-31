"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/shared/ui/button";
import { BarChart3, Bell, User } from "lucide-react";
import { cn } from "@/shared/lib/utils";
import { env } from "@/shared/config/env";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", href: "/" },
  { id: "analytics", label: "Analytics", href: "/analytics" },
];

export function Navbar({ activeTab }: { activeTab?: string }) {
  const path = usePathname();
  const current = activeTab ?? (path?.startsWith("/analytics") ? "analytics" : "dashboard");

  return (
    <nav className="bg-card border-b">
      <div className="px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary/70 grid place-items-center">
            <BarChart3 className="text-white w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold">{env.appName}</h1>
            <p className="text-xs text-muted-foreground">Food Service Intelligence</p>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-1 bg-muted/50 rounded-lg p-1">
          {NAV_ITEMS.map((item) => (
            <Link key={item.id} href={item.href}>
              <Button
                variant={current === item.id ? "default" : "ghost"}
                size="sm"
                className={cn(current === item.id && "bg-primary text-primary-foreground shadow-md")}
              >
                {item.label}
              </Button>
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon">
            <Bell className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon">
            <User className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </nav>
  );
}
