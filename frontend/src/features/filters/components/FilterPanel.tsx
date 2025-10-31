"use client";

import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Calendar, RefreshCw, TrendingUp } from "lucide-react";

export default function FilterPanel() {
  return (
    <Card className="p-3 bg-gradient-to-br from-card to-muted/20 border-border/50">
      <div className="flex flex-wrap items-center gap-2">
        <Select defaultValue="7days">
          <SelectTrigger className="w-[160px] bg-background text-sm">
            <Calendar className="w-4 h-4 mr-2 text-muted-foreground" />
            <SelectValue placeholder="Período" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="today">Hoje</SelectItem>
            <SelectItem value="7days">Últimos 7 dias</SelectItem>
            <SelectItem value="30days">Últimos 30 dias</SelectItem>
            <SelectItem value="90days">Últimos 90 dias</SelectItem>
            <SelectItem value="custom">Personalizado</SelectItem>
          </SelectContent>
        </Select>

        <Select defaultValue="all">
          <SelectTrigger className="w-[160px] bg-background text-sm">
            <SelectValue placeholder="Canal" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os canais</SelectItem>
            <SelectItem value="ifood">iFood</SelectItem>
            <SelectItem value="rappi">Rappi</SelectItem>
            <SelectItem value="presencial">Presencial</SelectItem>
            <SelectItem value="app">App Próprio</SelectItem>
          </SelectContent>
        </Select>

        <Button variant="outline" size="sm" className="ml-auto border-primary/20 hover:bg-primary/5 text-xs">
          <TrendingUp className="w-4 h-4 mr-2" /> Comparar períodos
        </Button>

        <Button variant="ghost" size="sm">
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>
    </Card>
  );
}
