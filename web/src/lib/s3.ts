import { S3Client, GetObjectCommand, PutObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'

const isLocal = process.env.NODE_ENV === 'development'

export const s3 = new S3Client({
  region: process.env.AWS_REGION ?? 'ap-northeast-2',
  ...(isLocal && {
    endpoint: process.env.S3_ENDPOINT ?? 'http://localhost:9000',
    forcePathStyle: true, // MinIO 필수
    credentials: {
      accessKeyId: process.env.MINIO_ROOT_USER ?? 'vibesafe_minio_user',
      secretAccessKey: process.env.MINIO_ROOT_PASSWORD ?? 'vibesafe_minio_password',
    },
  }),
  ...(!isLocal && {
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
    },
  }),
})

export const BUCKETS = {
  uploads: process.env.S3_BUCKET_UPLOADS ?? 'vibesafe-uploads',
  artifacts: process.env.S3_BUCKET_ARTIFACTS ?? 'vibesafe-artifacts',
}

/** 업로드용 presigned PUT URL 발급 (15분 유효) */
export async function createUploadPresignedUrl(scanId: string, fileName: string): Promise<{ url: string; s3Key: string }> {
  const s3Key = `uploads/${scanId}/${fileName}`
  const command = new PutObjectCommand({
    Bucket: BUCKETS.uploads,
    Key: s3Key,
    ContentType: 'application/octet-stream',
  })
  const url = await getSignedUrl(s3, command, { expiresIn: 900 })
  return { url, s3Key }
}

/** 다운로드용 presigned GET URL 발급 (10분 유효) */
export async function createDownloadPresignedUrl(bucket: string, s3Key: string): Promise<string> {
  const command = new GetObjectCommand({ Bucket: bucket, Key: s3Key })
  return getSignedUrl(s3, command, { expiresIn: 600 })
}
