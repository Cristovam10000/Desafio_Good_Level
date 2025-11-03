"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChannelRow } from "@/shared/api/sections";

export type ChannelSelection = {
  key: string;
  channelId: number;
  storeId: number | null;
};

export function useChannelSelection(channels?: ChannelRow[]) {
  const [selection, setSelection] = useState<ChannelSelection | null>(null);

  const handleSelect = useCallback(
    (value: string) => {
      if (value === "all") {
        setSelection(null);
        return;
      }
      const selected = channels?.find(
        (channel) => (channel.channel_store_key ?? `${channel.channel_id}:${channel.store_id}`) === value
      );
      if (!selected) {
        setSelection(null);
        return;
      }
      setSelection({
        key: value,
        channelId: selected.channel_id,
        storeId: selected.store_id ?? null,
      });
    },
    [channels]
  );

  useEffect(() => {
    if (!selection) return;
    const exists = channels?.some(
      (channel) => (channel.channel_store_key ?? `${channel.channel_id}:${channel.store_id}`) === selection.key
    );
    if (!exists) {
      setSelection(null);
    }
  }, [channels, selection]);

  const channelKey = useMemo(() => selection?.key ?? "all", [selection]);
  const channelId = selection?.channelId ?? null;
  const storeId = selection?.storeId ?? null;

  return {
    selection,
    setSelection,
    handleSelect,
    channelKey,
    channelId,
    storeId,
  };
}
