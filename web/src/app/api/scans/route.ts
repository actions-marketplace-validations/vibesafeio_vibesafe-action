import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { enqueueScanTask } from '@/lib/celery'

const VALID_DOMAINS = ['ecommerce', 'game', 'platform', 'healthcare', 'fintech', 'education']
const VALID_DEPTHS = ['quick', 'standard', 'deep']
const MAX_CONCURRENT_SCANS = 3

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { scanId, s3Key, domainType, scanDepth } = await req.json()

  if (!scanId || !s3Key || !domainType) {
    return NextResponse.json({ error: 'scanId, s3Key, domainType 필드가 필요합니다' }, { status: 400 })
  }

  if (!VALID_DOMAINS.includes(domainType)) {
    return NextResponse.json({ error: `유효하지 않은 도메인: ${domainType}` }, { status: 400 })
  }

  const depth = VALID_DEPTHS.includes(scanDepth) ? scanDepth : 'standard'

  // 동시 스캔 수 제한 (사용자당 3건)
  const runningCount = await prisma.scan.count({
    where: { userId: session.user.id, status: { in: ['PENDING', 'QUEUED', 'RUNNING'] } },
  })

  if (runningCount >= MAX_CONCURRENT_SCANS) {
    return NextResponse.json(
      { error: `동시 스캔은 최대 ${MAX_CONCURRENT_SCANS}건까지 가능합니다. 진행 중인 스캔이 완료된 후 시도해주세요.` },
      { status: 429 }
    )
  }

  // DB에 스캔 레코드 생성
  const scan = await prisma.scan.create({
    data: {
      id: scanId,
      userId: session.user.id,
      domainType,
      scanDepth: depth,
      status: 'PENDING',
      s3SourceKey: s3Key,
    },
  })

  // Celery 큐에 태스크 전달
  try {
    await enqueueScanTask({
      scanId,
      userId: session.user.id,
      s3Key,
      domainType,
      scanDepth: depth,
    })

    // 큐 전달 성공 → 상태 업데이트
    await prisma.scan.update({
      where: { id: scanId },
      data: { status: 'QUEUED' },
    })
  } catch (err) {
    // 큐 전달 실패 → FAILED 처리
    await prisma.scan.update({
      where: { id: scanId },
      data: { status: 'FAILED', errorMessage: '스캔 큐 등록에 실패했습니다. 잠시 후 다시 시도해주세요.' },
    })
    return NextResponse.json({ error: '스캔 시작에 실패했습니다' }, { status: 500 })
  }

  // 사용량 로그
  await prisma.usageLog.create({
    data: { userId: session.user.id, scanId, action: 'scan_submitted', metadata: { domainType, scanDepth: depth } },
  })

  return NextResponse.json({ scanId: scan.id, status: 'QUEUED' }, { status: 201 })
}
