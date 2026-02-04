-- CreateTable
CREATE TABLE "teams" (
    "id" SERIAL NOT NULL,
    "ncaa_id" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "mascot" TEXT,
    "division" INTEGER NOT NULL,
    "conference" TEXT NOT NULL,
    "season_id" INTEGER NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "teams_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "players" (
    "id" SERIAL NOT NULL,
    "ncaa_id" INTEGER,
    "first_name" TEXT NOT NULL,
    "last_name" TEXT NOT NULL,
    "position" TEXT,
    "class_year" TEXT,
    "team_id" INTEGER NOT NULL,
    "in_portal" BOOLEAN NOT NULL DEFAULT false,
    "portal_date" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "players_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "hitting_stats" (
    "id" SERIAL NOT NULL,
    "player_id" INTEGER NOT NULL,
    "g" INTEGER NOT NULL DEFAULT 0,
    "ab" INTEGER NOT NULL DEFAULT 0,
    "r" INTEGER NOT NULL DEFAULT 0,
    "h" INTEGER NOT NULL DEFAULT 0,
    "2b" INTEGER NOT NULL DEFAULT 0,
    "3b" INTEGER NOT NULL DEFAULT 0,
    "hr" INTEGER NOT NULL DEFAULT 0,
    "rbi" INTEGER NOT NULL DEFAULT 0,
    "bb" INTEGER NOT NULL DEFAULT 0,
    "k" INTEGER NOT NULL DEFAULT 0,
    "sb" INTEGER NOT NULL DEFAULT 0,
    "cs" INTEGER NOT NULL DEFAULT 0,
    "hbp" INTEGER NOT NULL DEFAULT 0,
    "sf" INTEGER NOT NULL DEFAULT 0,
    "avg" DOUBLE PRECISION,
    "obp" DOUBLE PRECISION,
    "slg" DOUBLE PRECISION,
    "ops" DOUBLE PRECISION,
    "xbh" INTEGER,
    "xbh_to_k" DOUBLE PRECISION,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "hitting_stats_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "pitching_stats" (
    "id" SERIAL NOT NULL,
    "player_id" INTEGER NOT NULL,
    "app" INTEGER NOT NULL DEFAULT 0,
    "gs" INTEGER NOT NULL DEFAULT 0,
    "w" INTEGER NOT NULL DEFAULT 0,
    "l" INTEGER NOT NULL DEFAULT 0,
    "sv" INTEGER NOT NULL DEFAULT 0,
    "ip" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "h" INTEGER NOT NULL DEFAULT 0,
    "r" INTEGER NOT NULL DEFAULT 0,
    "er" INTEGER NOT NULL DEFAULT 0,
    "bb" INTEGER NOT NULL DEFAULT 0,
    "k" INTEGER NOT NULL DEFAULT 0,
    "hr_allowed" INTEGER NOT NULL DEFAULT 0,
    "era" DOUBLE PRECISION,
    "whip" DOUBLE PRECISION,
    "k_per_9" DOUBLE PRECISION,
    "bb_per_9" DOUBLE PRECISION,
    "k_to_bb" DOUBLE PRECISION,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "pitching_stats_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" SERIAL NOT NULL,
    "email" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "name" TEXT,
    "email_alerts" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "favorites" (
    "id" SERIAL NOT NULL,
    "user_id" INTEGER NOT NULL,
    "player_id" INTEGER NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "favorites_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "portal_alerts" (
    "id" SERIAL NOT NULL,
    "user_id" INTEGER NOT NULL,
    "player_id" INTEGER NOT NULL,
    "sent_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "portal_alerts_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "teams_ncaa_id_key" ON "teams"("ncaa_id");

-- CreateIndex
CREATE INDEX "teams_division_idx" ON "teams"("division");

-- CreateIndex
CREATE INDEX "teams_conference_idx" ON "teams"("conference");

-- CreateIndex
CREATE INDEX "teams_name_idx" ON "teams"("name");

-- CreateIndex
CREATE UNIQUE INDEX "players_ncaa_id_key" ON "players"("ncaa_id");

-- CreateIndex
CREATE INDEX "players_last_name_first_name_idx" ON "players"("last_name", "first_name");

-- CreateIndex
CREATE INDEX "players_position_idx" ON "players"("position");

-- CreateIndex
CREATE INDEX "players_in_portal_idx" ON "players"("in_portal");

-- CreateIndex
CREATE INDEX "players_team_id_idx" ON "players"("team_id");

-- CreateIndex
CREATE UNIQUE INDEX "hitting_stats_player_id_key" ON "hitting_stats"("player_id");

-- CreateIndex
CREATE UNIQUE INDEX "pitching_stats_player_id_key" ON "pitching_stats"("player_id");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "favorites_user_id_idx" ON "favorites"("user_id");

-- CreateIndex
CREATE INDEX "favorites_player_id_idx" ON "favorites"("player_id");

-- CreateIndex
CREATE UNIQUE INDEX "favorites_user_id_player_id_key" ON "favorites"("user_id", "player_id");

-- CreateIndex
CREATE INDEX "portal_alerts_player_id_idx" ON "portal_alerts"("player_id");

-- CreateIndex
CREATE UNIQUE INDEX "portal_alerts_user_id_player_id_key" ON "portal_alerts"("user_id", "player_id");

-- AddForeignKey
ALTER TABLE "players" ADD CONSTRAINT "players_team_id_fkey" FOREIGN KEY ("team_id") REFERENCES "teams"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "hitting_stats" ADD CONSTRAINT "hitting_stats_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "pitching_stats" ADD CONSTRAINT "pitching_stats_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "favorites" ADD CONSTRAINT "favorites_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "favorites" ADD CONSTRAINT "favorites_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "portal_alerts" ADD CONSTRAINT "portal_alerts_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "portal_alerts" ADD CONSTRAINT "portal_alerts_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("id") ON DELETE CASCADE ON UPDATE CASCADE;
