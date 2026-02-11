"use client";

import { useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { PlayerFilters, Division } from "@/lib/types";

const POSITIONS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "P", "UT"];
const DIVISIONS: Division[] = ["D1", "D2", "D3"];
const CLASS_YEARS = ["Fr.", "So.", "Jr.", "Sr.", "Gr."];

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

  const isHitting = filters.statType === "hitting";
  const isPitching = filters.statType === "pitching";

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

      {/* Year */}
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Year</label>
        <select
          value={filters.classYear ?? ""}
          onChange={(e) => update({ classYear: e.target.value || undefined })}
          className="w-full rounded-md border border-input bg-background p-1.5 text-sm"
        >
          <option value="">All Years</option>
          {CLASS_YEARS.map((y) => (
            <option key={y} value={y}>{y}</option>
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

      {/* Hitting stat filters - only show when hitting is selected */}
      {isHitting && (
        <>
          <div className="border-t border-border pt-3">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Hitting Filters</span>
          </div>

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
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Min OBP</label>
            <Input
              type="number"
              step="0.001"
              min="0"
              max="1"
              placeholder=".400"
              value={filters.minObp ?? ""}
              onChange={(e) => update({ minObp: e.target.value ? parseFloat(e.target.value) : undefined })}
              className="h-8 text-sm"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Min SLG</label>
            <Input
              type="number"
              step="0.001"
              min="0"
              placeholder=".500"
              value={filters.minSlg ?? ""}
              onChange={(e) => update({ minSlg: e.target.value ? parseFloat(e.target.value) : undefined })}
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
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Min RBI</label>
            <Input
              type="number"
              step="1"
              min="0"
              placeholder="30"
              value={filters.minRBI ?? ""}
              onChange={(e) => update({ minRBI: e.target.value ? parseInt(e.target.value) : undefined })}
              className="h-8 text-sm"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Min SB</label>
            <Input
              type="number"
              step="1"
              min="0"
              placeholder="10"
              value={filters.minSB ?? ""}
              onChange={(e) => update({ minSB: e.target.value ? parseInt(e.target.value) : undefined })}
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
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Min AB</label>
            <Input
              type="number"
              step="1"
              min="0"
              placeholder="100"
              value={filters.minAB ?? ""}
              onChange={(e) => update({ minAB: e.target.value ? parseInt(e.target.value) : undefined })}
              className="h-8 text-sm"
            />
          </div>
        </>
      )}

      {/* Pitching stat filters - only show when pitching is selected */}
      {isPitching && (
        <>
          <div className="border-t border-border pt-3">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Pitching Filters</span>
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
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Max WHIP</label>
            <Input
              type="number"
              step="0.01"
              min="0"
              placeholder="1.20"
              value={filters.maxWhip ?? ""}
              onChange={(e) => update({ maxWhip: e.target.value ? parseFloat(e.target.value) : undefined })}
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

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Min K/BB</label>
            <Input
              type="number"
              step="0.1"
              min="0"
              placeholder="3.0"
              value={filters.minKToBb ?? ""}
              onChange={(e) => update({ minKToBb: e.target.value ? parseFloat(e.target.value) : undefined })}
              className="h-8 text-sm"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Min Wins</label>
            <Input
              type="number"
              step="1"
              min="0"
              placeholder="5"
              value={filters.minWins ?? ""}
              onChange={(e) => update({ minWins: e.target.value ? parseInt(e.target.value) : undefined })}
              className="h-8 text-sm"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Min Saves</label>
            <Input
              type="number"
              step="1"
              min="0"
              placeholder="5"
              value={filters.minSaves ?? ""}
              onChange={(e) => update({ minSaves: e.target.value ? parseInt(e.target.value) : undefined })}
              className="h-8 text-sm"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Min IP</label>
            <Input
              type="number"
              step="0.1"
              min="0"
              placeholder="50"
              value={filters.minIP ?? ""}
              onChange={(e) => update({ minIP: e.target.value ? parseFloat(e.target.value) : undefined })}
              className="h-8 text-sm"
            />
          </div>
        </>
      )}

      <Button variant="outline" size="sm" onClick={() => onFilterChange({})}>
        Reset Filters
      </Button>
    </div>
  );
}
