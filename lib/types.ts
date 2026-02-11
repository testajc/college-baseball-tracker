export type Division = "D1" | "D2" | "D3";

export interface PlayerWithStats {
  id: number;
  firstName: string;
  lastName: string;
  position: string | null;
  positions: string[];
  classYear: string | null;
  heightInches: number | null;
  weightLbs: number | null;
  bats: string | null;
  throws: string | null;
  hometown: string | null;
  highSchool: string | null;
  inPortal: boolean;
  portalDate: string | null;
  committedTo: string | null;
  team: {
    id: number;
    name: string;
    division: Division;
    conference: string;
  };
  hittingStats: HittingStatsData | null;
  pitchingStats: PitchingStatsData | null;
}

export interface HittingStatsData {
  season: number;
  g: number;
  ab: number;
  r: number;
  h: number;
  doubles: number;
  triples: number;
  hr: number;
  rbi: number;
  bb: number;
  k: number;
  sb: number;
  cs: number;
  hbp: number;
  sf: number;
  sh: number;
  gidp: number;
  avg: number | null;
  obp: number | null;
  slg: number | null;
  ops: number | null;
  xbh: number | null;
  xbhToK: number | null;
  tb: number | null;
}

export interface PitchingStatsData {
  season: number;
  app: number;
  gs: number;
  w: number;
  l: number;
  sv: number;
  cg: number;
  sho: number;
  ip: number;
  h: number;
  r: number;
  er: number;
  bb: number;
  k: number;
  hrAllowed: number;
  hb: number;
  wp: number;
  bk: number;
  era: number | null;
  whip: number | null;
  kPer9: number | null;
  bbPer9: number | null;
  kToBb: number | null;
  hPer9: number | null;
}

export interface TeamWithCount {
  id: number;
  ncaaId: number;
  name: string;
  mascot: string | null;
  division: Division;
  conference: string;
  state: string | null;
  _count: { players: number };
}

export interface PlayerFilters {
  search?: string;
  division?: Division;
  position?: string;
  conference?: string;
  classYear?: string;
  teamId?: number;
  inPortal?: boolean;
  statType?: "hitting" | "pitching";
  // Hitting stats
  minAvg?: number;
  minObp?: number;
  minSlg?: number;
  minOps?: number;
  minHR?: number;
  minRBI?: number;
  minSB?: number;
  minXbhToK?: number;
  // Pitching stats
  maxEra?: number;
  maxWhip?: number;
  minKPer9?: number;
  maxBB9?: number;
  minKToBb?: number;
  minWins?: number;
  minSaves?: number;
}
