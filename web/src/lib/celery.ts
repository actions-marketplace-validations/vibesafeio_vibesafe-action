/**
 * Next.js → Python Celery Worker 큐잉
 * Celery kombu 메시지 포맷으로 Redis에 LPUSH
 * Python worker는 기존 Redis 클라이언트로 수신
 */
import Redis from 'ioredis'

let redis: Redis | null = null

function getRedis(): Redis {
  if (!redis) {
    redis = new Redis(process.env.REDIS_URL ?? 'redis://:vibesafe_dev_redis@localhost:6379/0', {
      maxRetriesPerRequest: 3,
      lazyConnect: true,
    })
  }
  return redis
}

export interface ScanTaskParams {
  scanId: string
  userId: string
  s3Key: string
  domainType: string
  scanDepth: string
}

/** Celery scan_pipeline 태스크를 Redis 큐에 적재 */
export async function enqueueScanTask(params: ScanTaskParams): Promise<void> {
  const client = getRedis()

  const taskId = crypto.randomUUID()
  const taskName = 'worker.tasks.scan_pipeline'

  // Celery 4.x kombu 메시지 포맷
  const message = {
    body: Buffer.from(
      JSON.stringify({
        id: taskId,
        task: taskName,
        args: [],
        kwargs: params,
        retries: 0,
        eta: null,
        expires: null,
        utc: true,
        callbacks: null,
        errbacks: null,
        timelimit: [300, 360], // [soft, hard] 초
        taskset: null,
        chord: null,
      })
    ).toString('base64'),
    'content-type': 'application/json',
    'content-encoding': 'utf-8',
    headers: {
      id: taskId,
      task: taskName,
      lang: 'py',
      retries: 0,
      timelimit: [300, 360],
    },
    properties: {
      correlation_id: taskId,
      reply_to: '',
      delivery_mode: 2, // persistent
      delivery_info: {
        exchange: '',
        routing_key: 'celery',
      },
      priority: 0,
    },
  }

  // Celery 기본 큐: 'celery'
  await client.lpush('celery', JSON.stringify(message))
}
