"use client";

import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Calendar, RefreshCw, TrendingUp } from "lucide-react";
import type { IsoRange } from "@/shared/lib/date";
import type { ChannelRow } from "@/shared/api/specials";

export type PeriodOption = "today" | "7days" | "30days" | "90days" | "custom";

type FilterPanelProps = {
  period: PeriodOption;
  range: IsoRange;
  onPeriodChange: (value: PeriodOption) => void;
  onCustomRangeChange: (range: IsoRange) => void;
  channelId: number | null;
  onChannelChange: (value: number | null) => void;
  channels: ChannelRow[];
  isChannelLoading: boolean;
  onRefresh: () => void;
};

const PERIOD_LABEL: Record<PeriodOption, string> = {
  today: "Hoje",
  "7days": "Últimos 7 dias",
  "30days": "Últimos 30 dias",
  "90days": "Últimos 90 dias",
  custom: "Personalizado",
};

export default function FilterPanel({
  period,
  range,
  onPeriodChange,
  onCustomRangeChange,
  channelId,
  onChannelChange,
  channels,
  isChannelLoading,
  onRefresh,
}: FilterPanelProps) {
  const handleStartChange = (value: string) => {
    if (!value) return;
    const start = value;
    const end = range.end < start ? start : range.end;
    onCustomRangeChange({ start, end });
  };

  const handleEndChange = (value: string) => {
    if (!value) return;
    const end = value;
    const start = range.start > end ? end : range.start;
    onCustomRangeChange({ start, end });
  };

  const uniqueChannels = [...channels].sort((a, b) => a.name.localeCompare(b.name));

  return (
    <Card className="p-3 bg-card/70 border-border/40 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={period} onValueChange={(value) => onPeriodChange(value as PeriodOption)}>
          <SelectTrigger className="w-[190px] bg-background text-sm">
            <Calendar className="w-4 h-4 mr-2 text-muted-foreground" />
            <SelectValue placeholder="Período" />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(PERIOD_LABEL).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {period === "custom" && (
          <div className="flex flex-wrap items-center gap-2">
            <Input
              type="date"
              value={range.start}
              max={range.end}
              onChange={(event) => handleStartChange(event.target.value)}
              className="h-9 text-sm w-[150px]"
            />
            <span className="text-sm text-muted-foreground">até</span>
            <Input
              type="date"
              value={range.end}
              min={range.start}
              onChange={(event) => handleEndChange(event.target.value)}
              className="h-9 text-sm w-[150px]"
            />
          </div>
        )}

        <Select
          value={channelId != null ? String(channelId) : "all"}
          onValueChange={(value) => onChannelChange(value === "all" ? null : Number(value))}
          disabled={isChannelLoading}
        >
          <SelectTrigger className="w-[200px] bg-background text-sm">
            <SelectValue placeholder="Canal" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os canais</SelectItem>
            {uniqueChannels.map((channel) => (
              <SelectItem key={channel.id} value={String(channel.id)}>
                {channel.name} <span className="text-xs text-muted-foreground">#{channel.id}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" className="border-primary/20 text-xs text-primary" disabled>
            <TrendingUp className="w-4 h-4 mr-2" /> Comparar períodos
          </Button>

          <Button variant="ghost" size="sm" onClick={onRefresh}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
