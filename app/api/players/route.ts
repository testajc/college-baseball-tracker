import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { Prisma, Division } from "@prisma/client";

export const dynamic = "force-dynamic";

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
  const classYear = params.get("classYear");
  const teamId = params.get("teamId") ? parseInt(params.get("teamId")!) : undefined;
  const inPortal = params.get("inPortal") === "true" ? true : undefined;
  const statType = params.get("statType") as "hitting" | "pitching" | null;
  const sortBy = params.get("sortBy") || "lastName";
  const sortDir = params.get("sortDir") === "desc" ? "desc" : "asc";

  // Hitting stat thresholds
  const minAvg = params.get("minAvg") ? parseFloat(params.get("minAvg")!) : undefined;
  const minObp = params.get("minObp") ? parseFloat(params.get("minObp")!) : undefined;
  const minSlg = params.get("minSlg") ? parseFloat(params.get("minSlg")!) : undefined;
  const minOps = params.get("minOps") ? parseFloat(params.get("minOps")!) : undefined;
  const minHR = params.get("minHR") ? parseInt(params.get("minHR")!) : undefined;
  const minRBI = params.get("minRBI") ? parseInt(params.get("minRBI")!) : undefined;
  const minSB = params.get("minSB") ? parseInt(params.get("minSB")!) : undefined;
  const minXbhToK = params.get("minXbhToK") ? parseFloat(params.get("minXbhToK")!) : undefined;
  const minAB = params.get("minAB") ? parseInt(params.get("minAB")!) : undefined;

  // Pitching stat thresholds
  const maxEra = params.get("maxEra") ? parseFloat(params.get("maxEra")!) : undefined;
  const maxWhip = params.get("maxWhip") ? parseFloat(params.get("maxWhip")!) : undefined;
  const minKPer9 = params.get("minKPer9") ? parseFloat(params.get("minKPer9")!) : undefined;
  const maxBB9 = params.get("maxBB9") ? parseFloat(params.get("maxBB9")!) : undefined;
  const minKToBb = params.get("minKToBb") ? parseFloat(params.get("minKToBb")!) : undefined;
  const minWins = params.get("minWins") ? parseInt(params.get("minWins")!) : undefined;
  const minSaves = params.get("minSaves") ? parseInt(params.get("minSaves")!) : undefined;
  const minIP = params.get("minIP") ? parseFloat(params.get("minIP")!) : undefined;

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
    if (classYear) where.classYear = classYear;
    if (inPortal !== undefined) where.inPortal = inPortal;

    // Hitting stat field filters (wrapped in 'is' for proper Prisma relation filtering)
    const hittingWhere: Prisma.HittingStatsWhereInput = {};
    if (minAvg !== undefined) hittingWhere.avg = { gte: minAvg };
    if (minObp !== undefined) hittingWhere.obp = { gte: minObp };
    if (minSlg !== undefined) hittingWhere.slg = { gte: minSlg };
    if (minOps !== undefined) hittingWhere.ops = { gte: minOps };
    if (minHR !== undefined) hittingWhere.hr = { gte: minHR };
    if (minRBI !== undefined) hittingWhere.rbi = { gte: minRBI };
    if (minSB !== undefined) hittingWhere.sb = { gte: minSB };
    if (minXbhToK !== undefined) hittingWhere.xbhToK = { gte: minXbhToK };
    if (minAB !== undefined) hittingWhere.ab = { gte: minAB };

    const hasHittingFilters = Object.keys(hittingWhere).length > 0;
    if (hasHittingFilters || statType === "hitting") {
      where.hittingStats = { is: hittingWhere };
    }

    // Pitching stat field filters
    const pitchingWhere: Prisma.PitchingStatsWhereInput = {};
    if (maxEra !== undefined) pitchingWhere.era = { lte: maxEra };
    if (maxWhip !== undefined) pitchingWhere.whip = { lte: maxWhip };
    if (minKPer9 !== undefined) pitchingWhere.kPer9 = { gte: minKPer9 };
    if (maxBB9 !== undefined) pitchingWhere.bbPer9 = { lte: maxBB9 };
    if (minKToBb !== undefined) pitchingWhere.kToBb = { gte: minKToBb };
    if (minWins !== undefined) pitchingWhere.w = { gte: minWins };
    if (minSaves !== undefined) pitchingWhere.sv = { gte: minSaves };
    if (minIP !== undefined) pitchingWhere.ip = { gte: minIP };

    const hasPitchingFilters = Object.keys(pitchingWhere).length > 0;
    if (hasPitchingFilters || statType === "pitching") {
      where.pitchingStats = { is: pitchingWhere };
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
    const msg = error instanceof Error ? error.message : String(error);
    console.error("Error fetching players:", msg, error);
    return NextResponse.json({ error: `Failed to fetch players: ${msg}` }, { status: 500 });
  }
}
