'use client'

interface Props { score: number; grade: string }

const GRADE_COLORS: Record<string, string> = {
  A: '#22c55e', B: '#84cc16', C: '#eab308', D: '#f97316', F: '#ef4444',
}

export function ScoreGauge({ score, grade }: Props) {
  const color = GRADE_COLORS[grade] ?? '#ef4444'
  const circumference = 2 * Math.PI * 54
  const offset = circumference * (1 - score / 100)

  return (
    <div className="flex flex-col items-center">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r="54" fill="none" stroke="#1e293b" strokeWidth="12" />
        <circle
          cx="70" cy="70" r="54" fill="none"
          stroke={color} strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
          style={{ transition: 'stroke-dashoffset 1s ease' }}
        />
        <text x="70" y="65" textAnchor="middle" fill={color} fontSize="32" fontWeight="900">{score}</text>
        <text x="70" y="87" textAnchor="middle" fill={color} fontSize="16">등급 {grade}</text>
      </svg>
      <p className="text-slate-400 text-sm mt-1">보안 점수</p>
    </div>
  )
}
