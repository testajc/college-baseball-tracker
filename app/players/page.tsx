"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { SearchBar } from "@/components/SearchBar";
import { FilterPanel } from "@/components/FilterPanel";
import { PlayerTable } from "@/components/PlayerTable";
import type { PlayerFilters, PlayerWithStats } from "@/lib/types";

export default function PlayersPage() {
  const { data: session } = useSession();
  const [players, setPlayers] = useState<PlayerWithStats[]>([]);
  const [filters, setFilters] = useState<PlayerFilters>({ statType: "hitting" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [conferences, setConferences] = useState<string[]>([]);
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set());
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    fetch("/api/teams", { cache: 'no-store' })
      .then((r) => r.json())
      .then((data) => setConferences(data.conferences ?? []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!session) return;
    fetch("/api/favorites")
      .then((r) => r.json())
      .then((data) => {
        const ids = new Set(data.favorites?.map((f: { player: { id: number } }) => f.player.id) ?? []) as Set<number>;
        setFavoriteIds(ids);
      })
      .catch(() => {});
  }, [session]);

  const fetchPlayers = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("limit", "50");
    if (filters.search) params.set("search", filters.search);
    if (filters.division) params.set("division", filters.division);
    if (filters.position) params.set("position", filters.position);
    if (filters.conference) params.set("conference", filters.conference);
    if (filters.classYear) params.set("classYear", filters.classYear);
    if (filters.teamId) params.set("teamId", String(filters.teamId));
    if (filters.inPortal) params.set("inPortal", "true");
    if (filters.statType) params.set("statType", filters.statType);
    // Hitting stat filters
    if (filters.minAvg) params.set("minAvg", String(filters.minAvg));
    if (filters.minObp) params.set("minObp", String(filters.minObp));
    if (filters.minSlg) params.set("minSlg", String(filters.minSlg));
    if (filters.minOps) params.set("minOps", String(filters.minOps));
    if (filters.minHR) params.set("minHR", String(filters.minHR));
    if (filters.minRBI) params.set("minRBI", String(filters.minRBI));
    if (filters.minSB) params.set("minSB", String(filters.minSB));
    if (filters.minXbhToK) params.set("minXbhToK", String(filters.minXbhToK));
    if (filters.minAB) params.set("minAB", String(filters.minAB));
    // Pitching stat filters
    if (filters.maxEra) params.set("maxEra", String(filters.maxEra));
    if (filters.maxWhip) params.set("maxWhip", String(filters.maxWhip));
    if (filters.minKPer9) params.set("minKPer9", String(filters.minKPer9));
    if (filters.maxBB9) params.set("maxBB9", String(filters.maxBB9));
    if (filters.minKToBb) params.set("minKToBb", String(filters.minKToBb));
    if (filters.minWins) params.set("minWins", String(filters.minWins));
    if (filters.minSaves) params.set("minSaves", String(filters.minSaves));
    if (filters.minIP) params.set("minIP", String(filters.minIP));

    try {
      setError(null);
      const res = await fetch(`/api/players?${params}`, { cache: 'no-store' });
      if (!res.ok) {
        const text = await res.text();
        setError(`API error ${res.status}: ${text.slice(0, 200)}`);
        setPlayers([]);
        return;
      }
      const data = await res.json();
      if (data.error) {
        setError(data.error);
        setPlayers([]);
        return;
      }
      setPlayers(data.players ?? []);
      setTotalPages(data.pagination?.totalPages ?? 1);
    } catch (e) {
      setError(`Fetch failed: ${e instanceof Error ? e.message : String(e)}`);
      setPlayers([]);
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => { fetchPlayers(); }, [fetchPlayers]);

  const handleSearch = useCallback((query: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: query || undefined }));
      setPage(1);
    }, 300);
  }, []);

  const handleFilterChange = useCallback((newFilters: PlayerFilters) => {
    setFilters(newFilters);
    setPage(1);
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Players</h1>
        <SearchBar onSearch={handleSearch} />
      </div>

      <div className="flex flex-col gap-4 lg:flex-row">
        <aside className="w-full shrink-0 lg:w-60">
          <FilterPanel filters={filters} conferences={conferences} onFilterChange={handleFilterChange} />
        </aside>

        <div className="min-w-0 flex-1">
          {error && (
            <div className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
              {error}
            </div>
          )}
          {loading ? (
            <div className="py-12 text-center text-muted-foreground">Loading...</div>
          ) : (
            <>
              <PlayerTable
                players={players}
                favoriteIds={favoriteIds}
                statType={filters.statType ?? "hitting"}
              />
              <div className="mt-4 flex items-center justify-center gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
                <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
                  Next
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
