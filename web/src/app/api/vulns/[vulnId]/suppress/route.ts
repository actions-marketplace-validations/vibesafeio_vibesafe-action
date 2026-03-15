import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

export async function POST(req: NextRequest, { params }: { params: { vulnId: string } }) {
  const session = await getServerSession(authOptions)
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { reason } = await req.json()

  if (!reason || typeof reason !== 'string') {
    return NextResponse.json({ error: '오탐 신고 사유를 입력해주세요' }, { status: 400 })
  }

  // 취약점이 해당 사용자의 것인지 확인
  const vuln = await prisma.vulnerability.findUnique({
    where: { vulnId: params.vulnId },
    include: { scan: { select: { userId: true } } },
  })

  if (!vuln) {
    return NextResponse.json({ error: '취약점을 찾을 수 없습니다' }, { status: 404 })
  }

  if (vuln.scan.userId !== session.user.id) {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }

  // 오탐 처리
  const updated = await prisma.vulnerability.update({
    where: { vulnId: params.vulnId },
    data: {
      status: 'suppressed',
      suppressionReason: reason,
      suppressedBy: session.user.id,
      suppressedAt: new Date(),
    },
  })

  // 사용량 로그
  await prisma.usageLog.create({
    data: {
      userId: session.user.id,
      scanId: vuln.scanId,
      action: 'false_positive_reported',
      metadata: { vulnId: params.vulnId, reason },
    },
  })

  return NextResponse.json({ success: true, vulnId: updated.vulnId })
}
