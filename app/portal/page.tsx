"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PlayerTable } from "@/components/PlayerTable";
import type { Division, PlayerWithStats } from "@/lib/types";

const DIVISIONS: (Division | undefined)[] = [undefined, "D1", "D2", "D3"];

export default function PortalPage() {
  const { data: session } = useSession();
  const [players, setPlayers] = useState<PlayerWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [division, setDivision] = useState<Division | undefined>();
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (division) params.set("division", division);

    fetch(`/api/portal?${params}`, { cache: 'no-store' })
      .then((r) => r.json())
      .then((data) => setPlayers(data.players ?? []))
      .catch(() => setPlayers([]))
      .finally(() => setLoading(false));
  }, [division]);

  useEffect(() => {
    if (!session) return;
    fetch("/api/favorites")
      .then((r) => r.json())
      .then((data) => {
        const ids = new Set(
          data.favorites?.map((f: { player: { id: number } }) => f.player.id) ?? []
        ) as Set<number>;
        setFavoriteIds(ids);
      })
      .catch(() => {});
  }, [session]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Transfer Portal</h1>
          <p className="text-sm text-muted-foreground">
            Players who have entered the transfer portal this season
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-sm">
            {players.length} player{players.length !== 1 ? "s" : ""}
          </Badge>
          <div className="flex gap-1">
            {DIVISIONS.map((d) => (
              <Button
                key={d ?? "all"}
                variant={division === d ? "default" : "outline"}
                size="sm"
                onClick={() => setDivision(d)}
              >
                {d ?? "All"}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="py-12 text-center text-muted-foreground">Loading...</div>
      ) : (
        <PlayerTable
          players={players}
          favoriteIds={favoriteIds}
          statType="hitting"
        />
      )}
    </div>
  );
}
