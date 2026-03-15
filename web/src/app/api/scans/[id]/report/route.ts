import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { createDownloadPresignedUrl, BUCKETS } from '@/lib/s3'

export async function GET(req: NextRequest, { params }: { params: { id: string } }) {
  const session = await getServerSession(authOptions)
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const scan = await prisma.scan.findUnique({
    where: { id: params.id },
    include: { artifacts: { where: { artifactType: 'report_pdf' } } },
  })

  if (!scan || scan.userId !== session.user.id) {
    return NextResponse.json({ error: '스캔을 찾을 수 없습니다' }, { status: 404 })
  }

  if (scan.status !== 'COMPLETED') {
    return NextResponse.json({ error: '리포트가 아직 생성되지 않았습니다' }, { status: 404 })
  }

  const pdfArtifact = scan.artifacts[0]
  if (!pdfArtifact) {
    return NextResponse.json({ error: 'PDF 리포트를 찾을 수 없습니다' }, { status: 404 })
  }

  const downloadUrl = await createDownloadPresignedUrl(pdfArtifact.s3Bucket, pdfArtifact.s3Key)

  // S3 presigned URL로 리다이렉트
  return NextResponse.redirect(downloadUrl)
}
