"use client";

import { useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { PlayerFilters, Division } from "@/lib/types";

const POSITIONS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "P", "UT"];
const DIVISIONS: Division[] = ["D1", "D2", "D3"];

interface FilterPanelProps {
  filters: PlayerFilters;
  conferences: string[];
  onFilterChange: (filters: PlayerFilters) => void;
}

export function FilterPanel({ filters, conferences, onFilterChange }: FilterPanelProps) {
  const update = useCallback(
    (partial: Partial<PlayerFilters>) => {
      onFilterChange({ ...filters, ...partial });
    },
    [filters, onFilterChange]
  );

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border p-4">
      <h3 className="font-semibold">Filters</h3>

      {/* Division */}
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Division</label>
        <select
          value={filters.division ?? ""}
          onChange={(e) => update({ division: (e.target.value as Division) || undefined })}
          className="w-full rounded-md border border-input bg-background p-1.5 text-sm"
        >
          <option value="">All Divisions</option>
          {DIVISIONS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {/* Position */}
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Position</label>
        <select
          value={filters.position ?? ""}
          onChange={(e) => update({ position: e.target.value || undefined })}
          className="w-full rounded-md border border-input bg-background p-1.5 text-sm"
        >
          <option value="">All Positions</option>
          {POSITIONS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </div>

      {/* Conference */}
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Conference</label>
        <select
          value={filters.conference ?? ""}
          onChange={(e) => update({ conference: e.target.value || undefined })}
          className="w-full rounded-md border border-input bg-background p-1.5 text-sm"
        >
          <option value="">All Conferences</option>
          {conferences.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* Stat type toggle */}
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Stat Type</label>
        <div className="flex gap-1">
          {(["hitting", "pitching"] as const).map((type) => (
            <Button
              key={type}
              variant={filters.statType === type ? "default" : "outline"}
              size="sm"
              className="flex-1 capitalize"
              onClick={() => update({ statType: filters.statType === type ? undefined : type })}
            >
              {type}
            </Button>
          ))}
        </div>
      </div>

      {/* Portal filter */}
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={filters.inPortal ?? false}
          onChange={(e) => update({ inPortal: e.target.checked || undefined })}
          className="rounded"
        />
        Portal only
      </label>

      {/* Stat thresholds */}
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Min AVG</label>
        <Input
          type="number"
          step="0.001"
          min="0"
          max="1"
          placeholder=".300"
          value={filters.minAvg ?? ""}
          onChange={(e) => update({ minAvg: e.target.value ? parseFloat(e.target.value) : undefined })}
          className="h-8 text-sm"
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Min OPS</label>
        <Input
          type="number"
          step="0.001"
          min="0"
          placeholder=".800"
          value={filters.minOps ?? ""}
          onChange={(e) => update({ minOps: e.target.value ? parseFloat(e.target.value) : undefined })}
          className="h-8 text-sm"
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Min HR</label>
        <Input
          type="number"
          step="1"
          min="0"
          placeholder="10"
          value={filters.minHR ?? ""}
          onChange={(e) => update({ minHR: e.target.value ? parseInt(e.target.value) : undefined })}
          className="h-8 text-sm"
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Min XBH:K</label>
        <Input
          type="number"
          step="0.01"
          min="0"
          placeholder="0.50"
          value={filters.minXbhToK ?? ""}
          onChange={(e) => update({ minXbhToK: e.target.value ? parseFloat(e.target.value) : undefined })}
          className="h-8 text-sm"
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Max ERA</label>
        <Input
          type="number"
          step="0.01"
          min="0"
          placeholder="3.00"
          value={filters.maxEra ?? ""}
          onChange={(e) => update({ maxEra: e.target.value ? parseFloat(e.target.value) : undefined })}
          className="h-8 text-sm"
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Min K/9</label>
        <Input
          type="number"
          step="0.1"
          min="0"
          placeholder="10.0"
          value={filters.minKPer9 ?? ""}
          onChange={(e) => update({ minKPer9: e.target.value ? parseFloat(e.target.value) : undefined })}
          className="h-8 text-sm"
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Max BB/9</label>
        <Input
          type="number"
          step="0.1"
          min="0"
          placeholder="3.0"
          value={filters.maxBB9 ?? ""}
          onChange={(e) => update({ maxBB9: e.target.value ? parseFloat(e.target.value) : undefined })}
          className="h-8 text-sm"
        />
      </div>

      <Button variant="outline" size="sm" onClick={() => onFilterChange({})}>
        Reset Filters
      </Button>
    </div>
  );
}
