/*
  Warnings:

  - Changed the type of `division` on the `teams` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.

*/
-- CreateEnum
CREATE TYPE "Division" AS ENUM ('D1', 'D2', 'D3');

-- CreateEnum
CREATE TYPE "ScrapeStatus" AS ENUM ('RUNNING', 'COMPLETED', 'FAILED');

-- CreateEnum
CREATE TYPE "NotificationType" AS ENUM ('PORTAL_ENTRY', 'PORTAL_COMMITMENT');

-- AlterTable
ALTER TABLE "favorites" ADD COLUMN     "alert_sent" BOOLEAN NOT NULL DEFAULT false;

-- AlterTable
ALTER TABLE "hitting_stats" ADD COLUMN     "gidp" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "season" INTEGER NOT NULL DEFAULT 2026,
ADD COLUMN     "sh" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "tb" INTEGER;

-- AlterTable
ALTER TABLE "pitching_stats" ADD COLUMN     "bk" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "cg" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "h_per_9" DOUBLE PRECISION,
ADD COLUMN     "hb" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "season" INTEGER NOT NULL DEFAULT 2026,
ADD COLUMN     "sho" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "wp" INTEGER NOT NULL DEFAULT 0;

-- AlterTable
ALTER TABLE "players" ADD COLUMN     "bats" TEXT,
ADD COLUMN     "committed_to" TEXT,
ADD COLUMN     "height_inches" INTEGER,
ADD COLUMN     "high_school" TEXT,
ADD COLUMN     "hometown" TEXT,
ADD COLUMN     "positions" TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN     "throws" TEXT,
ADD COLUMN     "weight_lbs" INTEGER;

-- AlterTable: add new columns
ALTER TABLE "teams" ADD COLUMN     "logo_url" TEXT,
ADD COLUMN     "state" TEXT,
ALTER COLUMN "season_id" SET DEFAULT 0;

-- Drop existing index on integer division column before type change
DROP INDEX IF EXISTS "teams_division_idx";

-- Convert integer division (1,2,3) to enum (D1,D2,D3)
ALTER TABLE "teams" ALTER COLUMN "division" TYPE "Division"
  USING (CASE "division"
    WHEN 1 THEN 'D1'
    WHEN 2 THEN 'D2'
    WHEN 3 THEN 'D3'
  END)::"Division";

-- AlterTable
ALTER TABLE "users" ADD COLUMN     "email_verified" BOOLEAN NOT NULL DEFAULT false;

-- CreateTable
CREATE TABLE "email_notifications" (
    "id" SERIAL NOT NULL,
    "user_id" INTEGER NOT NULL,
    "player_id" INTEGER NOT NULL,
    "type" "NotificationType" NOT NULL,
    "sent_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "email_notifications_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "scrape_logs" (
    "id" SERIAL NOT NULL,
    "started_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMP(3),
    "status" "ScrapeStatus" NOT NULL DEFAULT 'RUNNING',
    "division" "Division",
    "teams_scraped" INTEGER NOT NULL DEFAULT 0,
    "players_scraped" INTEGER NOT NULL DEFAULT 0,
    "errors" TEXT[] DEFAULT ARRAY[]::TEXT[],

    CONSTRAINT "scrape_logs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "email_notifications_user_id_idx" ON "email_notifications"("user_id");

-- CreateIndex
CREATE INDEX "email_notifications_player_id_idx" ON "email_notifications"("player_id");

-- CreateIndex
CREATE INDEX "hitting_stats_season_idx" ON "hitting_stats"("season");

-- CreateIndex
CREATE INDEX "hitting_stats_avg_idx" ON "hitting_stats"("avg");

-- CreateIndex
CREATE INDEX "hitting_stats_hr_idx" ON "hitting_stats"("hr");

-- CreateIndex
CREATE INDEX "pitching_stats_season_idx" ON "pitching_stats"("season");

-- CreateIndex
CREATE INDEX "pitching_stats_era_idx" ON "pitching_stats"("era");

-- CreateIndex
CREATE INDEX "pitching_stats_k_idx" ON "pitching_stats"("k");

-- CreateIndex
CREATE INDEX "teams_division_idx" ON "teams"("division");

-- AddForeignKey
ALTER TABLE "email_notifications" ADD CONSTRAINT "email_notifications_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
