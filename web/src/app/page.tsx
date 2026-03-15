import { ScanUploadForm } from '@/components/ScanUploadForm'

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-900 text-white">
      <div className="max-w-2xl mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-black mb-3">🛡️ VibeSafe</h1>
          <p className="text-slate-400 text-lg">
            바이브 코딩으로 만든 서비스의 보안을 자동으로 점검합니다
          </p>
          <div className="flex justify-center gap-6 mt-6 text-sm text-slate-500 flex-wrap">
            <span>✅ SAST · SCA · 시크릿 탐지</span>
            <span>✅ 도메인별 규제 준수</span>
            <span>✅ 원클릭 수정 제안</span>
          </div>
        </div>

        <div className="bg-slate-800/50 rounded-2xl p-8 border border-slate-700">
          <ScanUploadForm />
        </div>

        <p className="text-center text-slate-600 text-xs mt-8">
          업로드된 코드는 스캔 완료 후 30일 뒤 자동 삭제됩니다 · 학습 데이터로 사용하지 않습니다
        </p>
      </div>
    </main>
  )
}
