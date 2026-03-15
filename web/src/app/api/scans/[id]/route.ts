import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

export async function GET(req: NextRequest, { params }: { params: { id: string } }) {
  const session = await getServerSession(authOptions)
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const scan = await prisma.scan.findUnique({
    where: { id: params.id },
    include: {
      result: true,
      vulnerabilities: {
        orderBy: { finalScore: 'desc' },
        where: { status: 'open' },
      },
      artifacts: true,
    },
  })

  if (!scan) {
    return NextResponse.json({ error: '스캔을 찾을 수 없습니다' }, { status: 404 })
  }

  // 다른 사용자의 스캔에 접근 불가
  if (scan.userId !== session.user.id) {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }

  return NextResponse.json(scan)
}
