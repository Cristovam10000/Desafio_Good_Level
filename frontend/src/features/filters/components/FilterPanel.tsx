"use client";

import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Calendar, RefreshCw, TrendingUp, Store } from "lucide-react";
import type { IsoRange } from "@/shared/lib/date";

export type PeriodOption = "today" | "7days" | "30days" | "90days" | "custom";

export type ChannelFilterOption = {
  key: string;
  label: string;
  channelId: number;
  storeId: number | null;
  storeName: string;
  channelName: string;
};

type FilterPanelProps = {
  period: PeriodOption;
  range: IsoRange;
  onPeriodChange: (value: PeriodOption) => void;
  onCustomRangeChange: (range: IsoRange) => void;
  channelOption: ChannelFilterOption | null;
  onChannelChange: (option: ChannelFilterOption | null) => void;
  channels: ChannelFilterOption[];
  isChannelLoading: boolean;
  onRefresh: () => void;
  onFullPeriod?: () => void;
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
  channelOption,
  onChannelChange,
  channels,
  isChannelLoading,
  onRefresh,
  onFullPeriod,
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

  return (
    <Card className="p-4 bg-card border-border shadow-sm">
      <div className="flex flex-col gap-3">
        {/* Primeira linha: Filtros principais */}
        <div className="flex flex-wrap items-center gap-3">
          <Select value={period} onValueChange={(value) => onPeriodChange(value as PeriodOption)}>
            <SelectTrigger className="w-[190px] bg-background text-sm h-10">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <SelectValue placeholder="Período" />
              </div>
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
            <div className="flex items-center gap-2">
              <Input
                type="date"
                value={range.start}
                max={range.end}
                onChange={(event) => handleStartChange(event.target.value)}
                className="h-10 text-sm w-[150px]"
              />
              <span className="text-sm text-muted-foreground">até</span>
              <Input
                type="date"
                value={range.end}
                min={range.start}
                onChange={(event) => handleEndChange(event.target.value)}
                className="h-10 text-sm w-[150px]"
              />
            </div>
          )}

          <Select
            value={channelOption ? channelOption.key : "all"}
            onValueChange={(value) => {
              if (value === "all") {
                onChannelChange(null);
              } else {
                const option = channels.find((item) => item.key === value);
                onChannelChange(option ?? null);
              }
            }}
            disabled={isChannelLoading}
          >
            <SelectTrigger className="w-[260px] bg-background text-sm h-10 truncate">
              <div className="flex items-center gap-2">
                <Store className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <SelectValue placeholder="Todos os canais" />
              </div>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os canais</SelectItem>
              {channels.map((channel) => (
                <SelectItem key={channel.key} value={channel.key}>
                  <span className="truncate max-w-[220px] inline-block">{channel.label}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Ações à direita */}
          <div className="ml-auto flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              className="border-primary/20 text-primary hover:bg-primary/10 h-10"
              onClick={onFullPeriod}
              disabled={!onFullPeriod}
            >
              <TrendingUp className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Analisar Período Completo</span>
              <span className="sm:hidden">Período Completo</span>
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
