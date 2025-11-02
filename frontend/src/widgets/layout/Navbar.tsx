"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/shared/ui/button";
import { BarChart3, Bell, LogOut, Menu } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/shared/ui/sheet";
import { cn } from "@/shared/lib/utils";
import { env } from "@/shared/config/env";
import { useAuth } from "@/shared/hooks/useAuth";
import { useRouter } from "next/navigation";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", href: "/" },
  { id: "lojas", label: "Lojas", href: "/lojas" },
  { id: "vendas", label: "Vendas", href: "/vendas" },
  { id: "produtos", label: "Produtos", href: "/produtos" },
  { id: "entregas", label: "Entregas", href: "/entregas" },
  { id: "financeiro", label: "Financeiro", href: "/financeiro" },
  { id: "operacoes", label: "Operações", href: "/operacoes" },
  { id: "anomalias", label: "Anomalias", href: "/anomalias" },
];

export function Navbar({ activeTab }: { activeTab?: string }) {
  const [open, setOpen] = useState(false);
  const path = usePathname();
  
  // Detectar página ativa baseado na URL
  let current = activeTab ?? "dashboard";
  if (path) {
    if (path.startsWith("/lojas")) current = "lojas";
    else if (path.startsWith("/vendas")) current = "vendas";
    else if (path.startsWith("/produtos")) current = "produtos";
    else if (path.startsWith("/entregas")) current = "entregas";
    else if (path.startsWith("/financeiro")) current = "financeiro";
    else if (path.startsWith("/operacoes")) current = "operacoes";
    else if (path.startsWith("/anomalias")) current = "anomalias";
    else current = "dashboard";
  }
  
  const router = useRouter();
  const { auth, logout } = useAuth();

  const handleLogout = () => {
    logout();
    router.replace("/auth");
    setOpen(false);
  };

  const initials = auth?.user?.name
    ?.split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

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

        {/* Menu Desktop - escondido no mobile */}
        <div className="hidden md:flex items-center gap-1 bg-muted/50 rounded-lg p-1 max-w-full overflow-x-auto">
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

        {/* Menu Desktop - Ícones à direita */}
        <div className="hidden md:flex items-center gap-2">
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="w-5 h-5" />
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full" title="Menu do usuário">
                <div className="w-9 h-9 rounded-full bg-muted flex items-center justify-center font-semibold text-sm text-muted-foreground uppercase">
                  {initials || "?"}
                </div>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem onClick={handleLogout} className="text-red-600 focus:text-red-600 cursor-pointer">
                <LogOut className="mr-2 h-4 w-4" />
                <span>Sair</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Menu Mobile - Sheet com hamburguer */}
        <div className="flex md:hidden items-center gap-2">
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="w-5 h-5" />
          </Button>

          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" title="Menu">
                <Menu className="w-6 h-6" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[280px] sm:w-[320px]">
              <SheetHeader>
                <SheetTitle>Menu</SheetTitle>
              </SheetHeader>
              
              <div className="flex flex-col gap-4 mt-6">
                {/* Informações do Usuário */}
                <div className="flex items-center gap-3 pb-4 border-b">
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center font-bold text-lg text-primary">
                    {initials || "?"}
                  </div>
                  <div>
                    <p className="font-semibold">{auth?.user?.name || "Usuário"}</p>
                    <p className="text-xs text-muted-foreground">Bem-vindo</p>
                  </div>
                </div>

                {/* Navegação */}
                <div className="flex flex-col gap-2">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Navegação</p>
                  {NAV_ITEMS.map((item) => (
                    <Link key={item.id} href={item.href} onClick={() => setOpen(false)}>
                      <Button
                        variant={current === item.id ? "default" : "ghost"}
                        className={cn(
                          "w-full justify-start",
                          current === item.id && "bg-primary text-primary-foreground"
                        )}
                      >
                        {item.label}
                      </Button>
                    </Link>
                  ))}
                </div>

                {/* Botão Sair */}
                <div className="mt-auto pt-4 border-t">
                  <Button
                    variant="destructive"
                    className="w-full justify-start"
                    onClick={handleLogout}
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    Sair
                  </Button>
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </nav>
  );
}
