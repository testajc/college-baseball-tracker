import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { Prisma, Division } from "@prisma/client";

const VALID_DIVISIONS: Division[] = ["D1", "D2", "D3"];

export async function GET(req: NextRequest) {
  const params = req.nextUrl.searchParams;

  const page = Math.max(1, parseInt(params.get("page") || "1"));
  const limit = Math.min(100, Math.max(1, parseInt(params.get("limit") || "50")));
  const offset = (page - 1) * limit;

  const search = params.get("search")?.trim();
  const divisionRaw = params.get("division");
  const division = divisionRaw && VALID_DIVISIONS.includes(divisionRaw as Division)
    ? (divisionRaw as Division)
    : undefined;
  const position = params.get("position");
  const conference = params.get("conference");
  const teamId = params.get("teamId") ? parseInt(params.get("teamId")!) : undefined;
  const inPortal = params.get("inPortal") === "true" ? true : undefined;
  const statType = params.get("statType") as "hitting" | "pitching" | null;
  const sortBy = params.get("sortBy") || "lastName";
  const sortDir = params.get("sortDir") === "desc" ? "desc" : "asc";

  // Stat thresholds
  const minAvg = params.get("minAvg") ? parseFloat(params.get("minAvg")!) : undefined;
  const maxEra = params.get("maxEra") ? parseFloat(params.get("maxEra")!) : undefined;
  const minKPer9 = params.get("minKPer9") ? parseFloat(params.get("minKPer9")!) : undefined;
  const minOps = params.get("minOps") ? parseFloat(params.get("minOps")!) : undefined;
  const minHR = params.get("minHR") ? parseInt(params.get("minHR")!) : undefined;
  const maxBB9 = params.get("maxBB9") ? parseFloat(params.get("maxBB9")!) : undefined;
  const minXbhToK = params.get("minXbhToK") ? parseFloat(params.get("minXbhToK")!) : undefined;

  try {
    const where: Prisma.PlayerWhereInput = {};

    if (search) {
      where.OR = [
        { firstName: { contains: search, mode: "insensitive" } },
        { lastName: { contains: search, mode: "insensitive" } },
        { team: { name: { contains: search, mode: "insensitive" } } },
      ];
    }

    if (division) where.team = { ...where.team as object, division };
    if (conference) where.team = { ...where.team as object, conference };
    if (teamId) where.teamId = teamId;
    if (position) where.position = position;
    if (inPortal !== undefined) where.inPortal = inPortal;

    // Stat threshold filters
    if (minAvg !== undefined || minOps !== undefined || minHR !== undefined || minXbhToK !== undefined) {
      where.hittingStats = {
        ...where.hittingStats as object,
        ...(minAvg !== undefined && { avg: { gte: minAvg } }),
        ...(minOps !== undefined && { ops: { gte: minOps } }),
        ...(minHR !== undefined && { hr: { gte: minHR } }),
        ...(minXbhToK !== undefined && { xbhToK: { gte: minXbhToK } }),
      };
    }

    if (maxEra !== undefined || minKPer9 !== undefined || maxBB9 !== undefined) {
      where.pitchingStats = {
        ...where.pitchingStats as object,
        ...(maxEra !== undefined && { era: { lte: maxEra } }),
        ...(minKPer9 !== undefined && { kPer9: { gte: minKPer9 } }),
        ...(maxBB9 !== undefined && { bbPer9: { lte: maxBB9 } }),
      };
    }

    if (statType === "hitting") {
      where.hittingStats = { ...where.hittingStats as object, isNot: null } as Prisma.HittingStatsNullableRelationFilter;
    } else if (statType === "pitching") {
      where.pitchingStats = { ...where.pitchingStats as object, isNot: null } as Prisma.PitchingStatsNullableRelationFilter;
    }

    const [players, total] = await Promise.all([
      prisma.player.findMany({
        where,
        include: {
          team: { select: { id: true, name: true, division: true, conference: true } },
          hittingStats: true,
          pitchingStats: true,
        },
        orderBy: { [sortBy]: sortDir },
        skip: offset,
        take: limit,
      }),
      prisma.player.count({ where }),
    ]);

    return NextResponse.json({
      players,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (error) {
    console.error("Error fetching players:", error);
    return NextResponse.json({ error: "Failed to fetch players" }, { status: 500 });
  }
}
