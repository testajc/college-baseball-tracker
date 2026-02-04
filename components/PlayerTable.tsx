"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  type ColumnDef,
  type SortingState,
  flexRender,
} from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import { FavoriteButton } from "./FavoriteButton";
import type { PlayerWithStats } from "@/lib/types";

interface PlayerTableProps {
  players: PlayerWithStats[];
  favoriteIds: Set<number>;
  statType: "hitting" | "pitching";
}

export function PlayerTable({ players, favoriteIds, statType }: PlayerTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const columns = useMemo<ColumnDef<PlayerWithStats>[]>(() => {
    const base: ColumnDef<PlayerWithStats>[] = [
      {
        id: "favorite",
        header: "",
        cell: ({ row }) => (
          <FavoriteButton
            playerId={row.original.id}
            isFavorited={favoriteIds.has(row.original.id)}
          />
        ),
        size: 40,
        enableSorting: false,
      },
      {
        accessorKey: "lastName",
        header: "Name",
        cell: ({ row }) => (
          <Link href={`/players/${row.original.id}`} className="font-medium hover:text-primary">
            {row.original.lastName}, {row.original.firstName}
            {row.original.inPortal && (
              <Badge variant="destructive" className="ml-1.5 text-[10px]">PORTAL</Badge>
            )}
          </Link>
        ),
      },
      { accessorKey: "position", header: "Pos", size: 60 },
      { accessorKey: "classYear", header: "Yr", size: 50 },
      {
        id: "team",
        header: "Team",
        accessorFn: (row) => row.team.name,
        cell: ({ row }) => (
          <Link href={`/teams/${row.original.team.id}`} className="hover:text-primary">
            {row.original.team.name}
          </Link>
        ),
        size: 150,
      },
      {
        id: "division",
        header: "Div",
        accessorFn: (row) => row.team.division,
        size: 50,
      },
      {
        id: "conference",
        header: "Conf",
        accessorFn: (row) => row.team.conference || "-",
        size: 120,
      },
    ];

    if (statType === "hitting") {
      base.push(
        { id: "avg", header: "AVG", accessorFn: (r) => r.hittingStats?.avg?.toFixed(3) ?? "-", size: 60 },
        { id: "obp", header: "OBP", accessorFn: (r) => r.hittingStats?.obp?.toFixed(3) ?? "-", size: 60 },
        { id: "slg", header: "SLG", accessorFn: (r) => r.hittingStats?.slg?.toFixed(3) ?? "-", size: 60 },
        { id: "ops", header: "OPS", accessorFn: (r) => r.hittingStats?.ops?.toFixed(3) ?? "-", size: 60 },
        { id: "hr", header: "HR", accessorFn: (r) => r.hittingStats?.hr ?? "-", size: 45 },
        { id: "rbi", header: "RBI", accessorFn: (r) => r.hittingStats?.rbi ?? "-", size: 50 },
        { id: "h", header: "H", accessorFn: (r) => r.hittingStats?.h ?? "-", size: 45 },
        { id: "r", header: "R", accessorFn: (r) => r.hittingStats?.r ?? "-", size: 45 },
        { id: "bb", header: "BB", accessorFn: (r) => r.hittingStats?.bb ?? "-", size: 45 },
        { id: "k", header: "K", accessorFn: (r) => r.hittingStats?.k ?? "-", size: 45 },
        { id: "sb", header: "SB", accessorFn: (r) => r.hittingStats?.sb ?? "-", size: 45 },
        { id: "xbh", header: "XBH", accessorFn: (r) => r.hittingStats?.xbh ?? "-", size: 50 },
        { id: "xbhToK", header: "XBH:K", accessorFn: (r) => r.hittingStats?.xbhToK?.toFixed(2) ?? "-", size: 65 },
      );
    } else {
      base.push(
        { id: "era", header: "ERA", accessorFn: (r) => r.pitchingStats?.era?.toFixed(2) ?? "-", size: 60 },
        { id: "w", header: "W", accessorFn: (r) => r.pitchingStats?.w ?? "-", size: 40 },
        { id: "l", header: "L", accessorFn: (r) => r.pitchingStats?.l ?? "-", size: 40 },
        { id: "sv", header: "SV", accessorFn: (r) => r.pitchingStats?.sv ?? "-", size: 40 },
        { id: "ip", header: "IP", accessorFn: (r) => r.pitchingStats?.ip?.toFixed(1) ?? "-", size: 55 },
        { id: "k_p", header: "K", accessorFn: (r) => r.pitchingStats?.k ?? "-", size: 45 },
        { id: "bb_p", header: "BB", accessorFn: (r) => r.pitchingStats?.bb ?? "-", size: 45 },
        { id: "whip", header: "WHIP", accessorFn: (r) => r.pitchingStats?.whip?.toFixed(2) ?? "-", size: 65 },
        { id: "kPer9", header: "K/9", accessorFn: (r) => r.pitchingStats?.kPer9?.toFixed(1) ?? "-", size: 55 },
        { id: "bbPer9", header: "BB/9", accessorFn: (r) => r.pitchingStats?.bbPer9?.toFixed(1) ?? "-", size: 60 },
        { id: "kToBb", header: "K:BB", accessorFn: (r) => r.pitchingStats?.kToBb?.toFixed(2) ?? "-", size: 60 },
        { id: "hrAllowed", header: "HR", accessorFn: (r) => r.pitchingStats?.hrAllowed ?? "-", size: 45 },
      );
    }

    return base;
  }, [statType, favoriteIds]);

  const table = useReactTable({
    data: players,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead className="bg-muted text-xs uppercase text-muted-foreground">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((header) => (
                <th
                  key={header.id}
                  className="cursor-pointer px-3 py-2 hover:bg-accent"
                  style={{ width: header.getSize() }}
                  onClick={header.column.getToggleSortingHandler()}
                >
                  <div className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {{ asc: " \u2191", desc: " \u2193" }[header.column.getIsSorted() as string] ?? ""}
                  </div>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-t border-border hover:bg-muted/50">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
          {players.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-3 py-8 text-center text-muted-foreground">
                No players found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
