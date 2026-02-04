"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { PlayerTable } from "@/components/PlayerTable";
import type { PlayerWithStats } from "@/lib/types";

export default function FavoritesPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [players, setPlayers] = useState<PlayerWithStats[]>([]);
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [statType, setStatType] = useState<"hitting" | "pitching">("hitting");

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  useEffect(() => {
    if (!session) return;
    fetch("/api/favorites")
      .then((r) => r.json())
      .then((data) => {
        const favs = data.favorites ?? [];
        const playerList = favs.map((f: { player: PlayerWithStats }) => f.player);
        setPlayers(playerList);
        setFavoriteIds(new Set(playerList.map((p: PlayerWithStats) => p.id)));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [session]);

  if (status === "loading" || loading) {
    return <div className="py-12 text-center text-muted-foreground">Loading...</div>;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">My Favorites</h1>
        <div className="flex gap-1">
          {(["hitting", "pitching"] as const).map((type) => (
            <Button
              key={type}
              variant={statType === type ? "default" : "outline"}
              size="sm"
              className="capitalize"
              onClick={() => setStatType(type)}
            >
              {type}
            </Button>
          ))}
        </div>
      </div>

      {players.length === 0 && !loading ? (
        <div className="py-12 text-center text-muted-foreground">
          <p>No favorites yet.</p>
          <p className="mt-1 text-sm">
            Browse <a href="/players" className="text-primary hover:underline">players</a> and
            click the star icon to add favorites.
          </p>
        </div>
      ) : (
        <PlayerTable
          players={players}
          favoriteIds={favoriteIds}
          statType={statType}
        />
      )}
    </div>
  );
}
