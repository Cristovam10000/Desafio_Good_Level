import { addDays, formatISO, subDays } from "date-fns";

export type IsoRange = {
  start: string;
  end: string;
};

export function isoRangeForLastNDays(days: number): IsoRange {
  return isoRange(days, 0);
}

export function isoRange(days: number, offsetDays: number): IsoRange {
  const endDate = subDays(new Date(), offsetDays);
  const startDate = subDays(endDate, days);
  return {
    start: formatISO(startDate, { representation: "date" }),
    end: formatISO(endDate, { representation: "date" }),
  };
}

export function expandToDateTime(range: IsoRange): IsoRange {
  return {
    start: `${range.start}T00:00:00Z`,
    end: `${range.end}T23:59:59Z`,
  };
}

export function shiftRange(range: IsoRange, days: number): IsoRange {
  const startDate = addDays(new Date(range.start), days);
  const endDate = addDays(new Date(range.end), days);
  return {
    start: formatISO(startDate, { representation: "date" }),
    end: formatISO(endDate, { representation: "date" }),
  };
}
