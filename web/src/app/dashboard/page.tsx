import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { ScanStatusBadge } from '@/components/ScanStatusBadge'

const DOMAIN_LABELS: Record<string, string> = {
  ecommerce: '이커머스', game: '게임', platform: '플랫폼/SaaS',
  healthcare: '헬스케어', fintech: '핀테크', education: '교육',
}

export default async function DashboardPage() {
  const session = await getServerSession(authOptions)
  if (!session?.user?.id) redirect('/')

  const scans = await prisma.scan.findMany({
    where: { userId: session.user.id },
    orderBy: { createdAt: 'desc' },
    take: 20,
    include: { result: { select: { score: true, grade: true } } },
  })

  return (
    <main className="min-h-screen bg-slate-900 text-white">
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-black">📋 스캔 히스토리</h1>
          <Link href="/" className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm font-medium transition-colors">
            + 새 스캔
          </Link>
        </div>

        {scans.length === 0 ? (
          <div className="text-center py-20 text-slate-500">
            <p className="text-lg">아직 스캔 내역이 없습니다</p>
            <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mt-2 inline-block">
              첫 번째 스캔 시작하기 →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {scans.map(scan => (
              <Link
                key={scan.id}
                href={`/scan/${scan.id}`}
                className="block bg-slate-800 hover:bg-slate-750 border border-slate-700 hover:border-slate-600 rounded-xl p-4 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-white">
                        {DOMAIN_LABELS[scan.domainType] ?? scan.domainType}
                      </span>
                      <ScanStatusBadge status={scan.status} />
                    </div>
                    <p className="text-xs text-slate-500 mt-1 font-mono">{scan.id.slice(0, 16)}...</p>
                    <p className="text-xs text-slate-600 mt-1">
                      {new Date(scan.createdAt).toLocaleDateString('ko-KR', {
                        year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
                      })}
                    </p>
                  </div>
                  {scan.result && (
                    <div className="text-right">
                      <div
                        className="text-2xl font-black"
                        style={{ color: { A: '#22c55e', B: '#84cc16', C: '#eab308', D: '#f97316', F: '#ef4444' }[scan.result.grade] ?? '#ef4444' }}
                      >
                        {scan.result.score}
                      </div>
                      <div className="text-xs text-slate-500">점</div>
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  )
}
