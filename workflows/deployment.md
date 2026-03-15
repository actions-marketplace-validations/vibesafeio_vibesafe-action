# Workflow: 배포 프로세스 (deployment)

## 목표
VibeSafe 서비스를 프로덕션 환경에 안전하게 배포한다.

## 인프라 구성

### 필수 서비스
| 서비스 | 용도 | 구체적 기술 |
|--------|------|-----------|
| 웹 서버 | Next.js SSR + API Routes | Vercel 또는 AWS ECS Fargate |
| 스캔 워커 | 백그라운드 스캔 작업 실행 | AWS ECS Fargate (CPU-optimized) |
| 메시지 큐 | 스캔 작업 비동기 처리 | AWS SQS 또는 Redis Bull Queue |
| 데이터베이스 | 사용자, 스캔 결과, 수정 제안 저장 | PostgreSQL 16 (AWS RDS) |
| 캐시 | 세션, 규칙셋 캐싱 | Redis 7 (AWS ElastiCache) |
| 파일 저장소 | 업로드 파일, 스캔 결과, 리포트 | AWS S3 (서버사이드 암호화 AES-256) |
| 컨테이너 레지스트리 | Docker 이미지 저장 | AWS ECR |
| 샌드박스 | DAST용 격리 실행 환경 | Docker-in-Docker (AWS ECS, 네트워크 격리) |
| CDN | 정적 에셋, 프론트엔드 | CloudFront |
| 모니터링 | 메트릭, 로그, 알림 | Datadog 또는 Grafana + Loki |
| 시크릿 관리 | API 키, DB 비밀번호 | AWS Secrets Manager |

### 환경 분리
```
production/     → app.vibesafe.io      (사용자 서비스)
staging/        → staging.vibesafe.io  (QA 검증)
development/    → dev.vibesafe.io      (개발 테스트)
```

### 배포 체크리스트
1. [ ] 모든 환경 변수가 Secrets Manager에 등록되었는가
2. [ ] DB 마이그레이션이 staging에서 검증되었는가
3. [ ] 스캔 워커 Docker 이미지가 ECR에 푸시되었는가
4. [ ] S3 버킷 정책에서 퍼블릭 액세스가 차단되었는가
5. [ ] CloudFront 배포가 HTTPS 전용인가
6. [ ] 로드밸런서 헬스체크가 정상 응답하는가
7. [ ] 에러 알림 채널(Slack/PagerDuty)이 설정되었는가
8. [ ] 롤백 절차가 문서화되었는가

## 배포 순서
1. DB 마이그레이션 실행 (`prisma migrate deploy`)
2. 스캔 워커 이미지 빌드 및 ECR 푸시
3. ECS 서비스 업데이트 (Rolling Update, 최소 가용 50%)
4. 프론트엔드 빌드 및 Vercel/CloudFront 배포
5. 스모크 테스트 실행 (핵심 스캔 파이프라인 1회 통과 확인)
6. 모니터링 대시보드에서 에러율 확인 (5분간 0.1% 미만 유지)

## 롤백 절차
1. ECS 서비스를 이전 태스크 정의 리비전으로 롤백
2. 필요 시 DB 마이그레이션 롤백 (`prisma migrate rollback`)
3. CloudFront 캐시 무효화
4. 롤백 사유를 `workflows/error_log.md`에 기록

## 학습 기록
- [2025-03-15] 초기 작성
