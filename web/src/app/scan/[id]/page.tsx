'use client'
import { useEffect, useState } from 'react'
import { ScanStatusBadge } from '@/components/ScanStatusBadge'
import { ScoreGauge } from '@/components/ScoreGauge'
import { VulnerabilityList } from '@/components/VulnerabilityList'

interface ScanData {
  id: string
  status: string
  domainType: string
  errorMessage?: string
  result?: { score: number; grade: string; criticalCount: number; highCount: number; mediumCount: number; lowCount: number }
  vulnerabilities?: any[]
}

const DOMAIN_LABELS: Record<string, string> = {
  ecommerce: '이커머스', game: '게임', platform: '플랫폼/SaaS',
  healthcare: '헬스케어', fintech: '핀테크', education: '교육',
}

export default function ScanPage({ params }: { params: { id: string } }) {
  const [scan, setScan] = useState<ScanData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let stopped = false

    async function poll() {
      try {
        const res = await fetch(`/api/scans/${params.id}`)
        if (!res.ok) { setError('스캔 결과를 불러올 수 없습니다'); return }
        const data: ScanData = await res.json()
        if (!stopped) setScan(data)

        // 완료/실패 전까지 3초마다 폴링
        if (!stopped && !['COMPLETED', 'FAILED'].includes(data.status)) {
          setTimeout(poll, 3000)
        }
      } catch {
        if (!stopped) setError('네트워크 오류가 발생했습니다')
      }
    }

    poll()
    return () => { stopped = true }
  }, [params.id])

  if (error) return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <p className="text-red-400">{error}</p>
    </div>
  )

  if (!scan) return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-400">로딩 중...</p>
      </div>
    </div>
  )

  return (
    <main className="min-h-screen bg-slate-900 text-white">
      <div className="max-w-3xl mx-auto px-4 py-12">

        {/* 헤더 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-black">🛡️ 보안 스캔 결과</h1>
            <p className="text-slate-400 text-sm mt-1">
              {DOMAIN_LABELS[scan.domainType] ?? scan.domainType} · {params.id.slice(0, 8)}
            </p>
          </div>
          <ScanStatusBadge status={scan.status} />
        </div>

        {/* 스캔 중 안내 */}
        {['PENDING', 'QUEUED', 'RUNNING'].includes(scan.status) && (
          <div className="bg-slate-800 rounded-xl p-8 text-center border border-slate-700 mb-8">
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-slate-300 font-medium">보안 스캔이 진행 중입니다</p>
            <p className="text-slate-500 text-sm mt-2">완료되면 자동으로 결과가 표시됩니다</p>
          </div>
        )}

        {/* 실패 안내 */}
        {scan.status === 'FAILED' && (
          <div className="bg-red-950 rounded-xl p-6 border border-red-800 mb-8">
            <p className="text-red-400 font-medium">스캔에 실패했습니다</p>
            {scan.errorMessage && <p className="text-red-500 text-sm mt-2">{scan.errorMessage}</p>}
          </div>
        )}

        {/* 결과 */}
        {scan.result && (
          <>
            {/* 점수 + 카운트 */}
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 mb-6">
              <div className="flex items-center gap-8">
                <ScoreGauge score={scan.result.score} grade={scan.result.grade} />
                <div className="grid grid-cols-2 gap-4 flex-1">
                  {[
                    { label: '치명적', count: scan.result.criticalCount, color: 'text-red-400' },
                    { label: '높음',   count: scan.result.highCount,     color: 'text-orange-400' },
                    { label: '보통',   count: scan.result.mediumCount,   color: 'text-yellow-400' },
                    { label: '낮음',   count: scan.result.lowCount,      color: 'text-slate-400' },
                  ].map(item => (
                    <div key={item.label} className="text-center">
                      <div className={`text-3xl font-black ${item.color}`}>{item.count}</div>
                      <div className="text-xs text-slate-500 mt-1">{item.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* 취약점 목록 */}
            <div className="mb-6">
              <h2 className="text-lg font-bold mb-4">취약점 목록 (우선순위순)</h2>
              <VulnerabilityList items={scan.vulnerabilities ?? []} />
            </div>

            {/* PDF 다운로드 */}
            <div className="text-center">
              <a
                href={`/api/scans/${params.id}/report`}
                className="inline-flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 rounded-xl text-sm font-medium transition-colors"
              >
                📄 PDF 리포트 다운로드
              </a>
            </div>
          </>
        )}
      </div>
    </main>
  )
}
