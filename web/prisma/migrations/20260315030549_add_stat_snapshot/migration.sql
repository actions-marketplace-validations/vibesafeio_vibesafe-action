-- CreateTable
CREATE TABLE "vuln_stat_snapshots" (
    "id" TEXT NOT NULL,
    "domain_type" TEXT NOT NULL,
    "detected_stack" JSONB NOT NULL,
    "total_vulns" INTEGER NOT NULL DEFAULT 0,
    "critical_count" INTEGER NOT NULL DEFAULT 0,
    "high_count" INTEGER NOT NULL DEFAULT 0,
    "medium_count" INTEGER NOT NULL DEFAULT 0,
    "low_count" INTEGER NOT NULL DEFAULT 0,
    "vuln_type_counts" JSONB NOT NULL,
    "security_score" INTEGER NOT NULL,
    "security_grade" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "vuln_stat_snapshots_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "vuln_stat_snapshots_domain_type_idx" ON "vuln_stat_snapshots"("domain_type");

-- CreateIndex
CREATE INDEX "vuln_stat_snapshots_created_at_idx" ON "vuln_stat_snapshots"("created_at" DESC);
