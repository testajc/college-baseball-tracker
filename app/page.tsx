import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="flex flex-col items-center gap-8 py-12 text-center">
      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
        College Baseball Tracker
      </h1>
      <p className="max-w-lg text-lg text-muted-foreground">
        Search and filter D1, D2, and D3 baseball stats. Track the transfer portal.
        Favorite players and get email alerts.
      </p>

      <div className="flex flex-wrap justify-center gap-4">
        <Button asChild size="lg">
          <Link href="/players">Browse Players</Link>
        </Button>
        <Button variant="outline" asChild size="lg">
          <Link href="/teams">Browse Teams</Link>
        </Button>
        <Button variant="outline" asChild size="lg">
          <Link href="/portal">Transfer Portal</Link>
        </Button>
      </div>

      <div className="mt-8 grid gap-6 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>All Divisions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              D1, D2, and D3 hitting and pitching stats from stats.ncaa.org for the current 2025-26 season.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Advanced Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Filter by division, position, conference, and stat thresholds like ERA &lt; 3.00 or AVG &gt; .300.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Portal Alerts</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Favorite players and get notified by email when they enter the transfer portal.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
