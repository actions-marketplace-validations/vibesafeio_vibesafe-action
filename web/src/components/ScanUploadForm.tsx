'use client'
import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'

const DOMAINS = [
  { value: 'ecommerce', label: '이커머스', desc: 'PCI DSS · GDPR' },
  { value: 'game',      label: '게임',     desc: 'COPPA · GDPR' },
  { value: 'platform',  label: '플랫폼/SaaS', desc: 'SOC2 · GDPR' },
  { value: 'healthcare',label: '헬스케어', desc: 'HIPAA · 개인정보보호법' },
  { value: 'fintech',   label: '핀테크',   desc: 'PCI DSS · 전자금융거래법' },
  { value: 'education', label: '교육',     desc: 'FERPA · COPPA' },
]

const DEPTHS = [
  { value: 'quick',    label: '빠른 스캔',   desc: '코드 분석만 (1-2분)' },
  { value: 'standard', label: '표준 스캔',   desc: '코드 + 의존성 분석 (3-5분)' },
  { value: 'deep',     label: '심층 스캔',   desc: '전체 분석 + 런타임 테스트 (10분+)' },
]

export function ScanUploadForm() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [domain, setDomain] = useState('')
  const [depth, setDepth] = useState('standard')
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !domain) { setError('파일과 서비스 유형을 선택해주세요'); return }
    setError('')
    setUploading(true)

    try {
      // 1. Presigned URL 발급
      setProgress(10)
      const presignRes = await fetch('/api/scans/presign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fileName: file.name, fileSize: file.size }),
      })
      if (!presignRes.ok) throw new Error((await presignRes.json()).error)
      const { scanId, presignedUrl, s3Key } = await presignRes.json()

      // 2. S3 직접 업로드
      setProgress(30)
      const uploadRes = await fetch(presignedUrl, { method: 'PUT', body: file })
      if (!uploadRes.ok) throw new Error('파일 업로드에 실패했습니다')

      // 3. 스캔 시작
      setProgress(80)
      const scanRes = await fetch('/api/scans', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scanId, s3Key, domainType: domain, scanDepth: depth }),
      })
      if (!scanRes.ok) throw new Error((await scanRes.json()).error)

      setProgress(100)
      router.push(`/scan/${scanId}`)
    } catch (err: any) {
      setError(err.message ?? '알 수 없는 오류가 발생했습니다')
      setUploading(false)
      setProgress(0)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* 파일 업로드 */}
      <div
        className="border-2 border-dashed border-slate-600 rounded-xl p-10 text-center cursor-pointer hover:border-blue-500 transition-colors"
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".zip,.tar.gz,.tgz,.js,.ts,.py"
          onChange={e => setFile(e.target.files?.[0] ?? null)}
        />
        {file ? (
          <div>
            <p className="text-white font-semibold">{file.name}</p>
            <p className="text-slate-400 text-sm mt-1">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
          </div>
        ) : (
          <div>
            <p className="text-slate-300 text-lg">ZIP, TAR.GZ 또는 소스 파일을 드래그하거나 클릭</p>
            <p className="text-slate-500 text-sm mt-2">최대 500MB</p>
          </div>
        )}
      </div>

      {/* 도메인 선택 */}
      <div>
        <h3 className="text-white font-semibold mb-3">서비스 유형</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {DOMAINS.map(d => (
            <button
              key={d.value}
              type="button"
              onClick={() => setDomain(d.value)}
              className={`p-3 rounded-lg border text-left transition-colors ${
                domain === d.value
                  ? 'border-blue-500 bg-blue-500/10 text-white'
                  : 'border-slate-600 text-slate-300 hover:border-slate-400'
              }`}
            >
              <div className="font-medium">{d.label}</div>
              <div className="text-xs text-slate-400 mt-1">{d.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 스캔 깊이 */}
      <div>
        <h3 className="text-white font-semibold mb-3">스캔 유형</h3>
        <div className="grid grid-cols-3 gap-3">
          {DEPTHS.map(d => (
            <button
              key={d.value}
              type="button"
              onClick={() => setDepth(d.value)}
              className={`p-3 rounded-lg border text-left transition-colors ${
                depth === d.value
                  ? 'border-blue-500 bg-blue-500/10 text-white'
                  : 'border-slate-600 text-slate-300 hover:border-slate-400'
              }`}
            >
              <div className="font-medium">{d.label}</div>
              <div className="text-xs text-slate-400 mt-1">{d.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {uploading && (
        <div className="space-y-2">
          <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-slate-400 text-sm text-center">
            {progress < 30 ? 'URL 준비 중...' : progress < 80 ? '파일 업로드 중...' : '스캔 시작 중...'}
          </p>
        </div>
      )}

      <button
        type="submit"
        disabled={uploading || !file || !domain}
        className="w-full py-4 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold rounded-xl transition-colors"
      >
        {uploading ? '처리 중...' : '🔍 보안 스캔 시작'}
      </button>
    </form>
  )
}
