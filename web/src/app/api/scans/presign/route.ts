import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { createUploadPresignedUrl } from '@/lib/s3'
import { randomUUID } from 'crypto'

const MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024 // 500MB

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { fileName, fileSize } = await req.json()

  if (!fileName || typeof fileName !== 'string') {
    return NextResponse.json({ error: '파일 이름이 필요합니다' }, { status: 400 })
  }

  if (fileSize && fileSize > MAX_FILE_SIZE_BYTES) {
    return NextResponse.json(
      { error: `파일 크기가 너무 큽니다. 최대 500MB까지 허용됩니다.` },
      { status: 413 }
    )
  }

  const scanId = randomUUID()
  const { url, s3Key } = await createUploadPresignedUrl(scanId, fileName)

  return NextResponse.json({ scanId, presignedUrl: url, s3Key })
}
