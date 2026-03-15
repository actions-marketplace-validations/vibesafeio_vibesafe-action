'use client'

const STATUS_CONFIG: Record<string, { label: string; color: string; animate: boolean }> = {
  PENDING:   { label: '대기 중',    color: 'text-slate-400 border-slate-600',   animate: false },
  QUEUED:    { label: '큐 등록됨',  color: 'text-blue-400 border-blue-600',     animate: true },
  RUNNING:   { label: '스캔 중',    color: 'text-yellow-400 border-yellow-600', animate: true },
  COMPLETED: { label: '완료',       color: 'text-green-400 border-green-600',   animate: false },
  FAILED:    { label: '실패',       color: 'text-red-400 border-red-600',       animate: false },
}

export function ScanStatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.PENDING
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-sm font-medium ${config.color}`}>
      {config.animate && (
        <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
      )}
      {config.label}
    </span>
  )
}
