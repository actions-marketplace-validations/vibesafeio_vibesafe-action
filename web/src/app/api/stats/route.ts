import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

// GET /api/stats — 익명 집계 통계 (공개 엔드포인트)
export async function GET() {
  const [totalScans, domainStats, gradeDistribution, topVulnTypes] = await Promise.all([
    prisma.vulnStatSnapshot.count(),

    prisma.vulnStatSnapshot.groupBy({
      by: ['domainType'],
      _avg: { securityScore: true, totalVulns: true },
      _count: true,
      orderBy: { _count: { domainType: 'desc' } },
    }),

    prisma.vulnStatSnapshot.groupBy({
      by: ['securityGrade'],
      _count: true,
      orderBy: { securityGrade: 'asc' },
    }),

    // jsonb_each_text로 vulnTypeCounts 집계
    prisma.$queryRaw<{ type: string; count: bigint }[]>`
      SELECT key AS type, SUM(value::int) AS count
      FROM vuln_stat_snapshots, jsonb_each_text(vuln_type_counts)
      GROUP BY key
      ORDER BY count DESC
      LIMIT 10
    `,
  ])

  return NextResponse.json({
    totalScans,
    domainStats: domainStats.map((d) => ({
      domain: d.domainType,
      avgScore: Math.round(d._avg.securityScore ?? 0),
      avgVulns: Math.round(d._avg.totalVulns ?? 0),
      scanCount: d._count,
    })),
    gradeDistribution: gradeDistribution.map((g) => ({
      grade: g.securityGrade,
      count: g._count,
    })),
    topVulnTypes: topVulnTypes.map((r) => ({
      type: r.type,
      count: Number(r.count),
    })),
  })
}
