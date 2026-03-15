# VibeSafe 🛡️

바이브 코더(AI 기반 개발자)를 위한 보안 스캐닝 서비스.
개발 지식 없이도 OWASP Top 10, 도메인별 규제(PCI DSS, HIPAA, GDPR 등)를 자동으로 검사하고 원클릭 수정까지 제공한다.

## 아키텍처: WAT 프레임워크

```
Workflows (workflows/*.md)   — 각 작업의 SOP 지침서
    ↓
Agents (Claude Code)         — 워크플로우를 읽고 도구를 순서대로 실행
    ↓
Tools (tools/**/*.py)        — 결정론적 실행 스크립트
```

## 프로젝트 구조

```
vibe_security/
├── .env.example             # 환경 변수 예시 (.env로 복사 후 값 채우기)
├── requirements.txt         # Python 의존성
├── AGENT_INSTRUCTIONS.md    # 에이전트 운영 지침
├── workflows/               # SOP 마크다운
│   ├── scan_submission.md
│   ├── domain_classification.md
│   ├── vulnerability_triage.md
│   ├── auto_remediation.md
│   ├── report_generation.md
│   ├── deployment.md
│   └── error_log.md
├── tools/
│   ├── infra/
│   │   ├── file_extractor.py      # 업로드 파일 압축 해제 및 검증
│   │   ├── sandbox_manager.py     # Docker 샌드박스 생성/폐기
│   │   └── db_client.py           # PostgreSQL/Redis 클라이언트
│   ├── scanner/
│   │   ├── sast_runner.py         # Semgrep 정적 분석
│   │   ├── dast_runner.py         # OWASP ZAP 동적 분석
│   │   ├── sca_runner.py          # 의존성 취약점 스캔
│   │   ├── secret_scanner.py      # 하드코딩 시크릿 탐지
│   │   └── domain_rule_engine.py  # 도메인 분류 + 규칙셋 매핑
│   ├── remediation/
│   │   ├── auto_fix_generator.py  # AI 기반 수정 코드 생성
│   │   ├── patch_applier.py       # 자동 패치 적용
│   │   └── fix_validator.py       # 수정 후 재스캔 검증
│   └── report/
│       ├── score_calculator.py    # 보안 점수 산출 (0-100)
│       ├── compliance_checker.py  # 규제 준수 판정
│       └── pdf_generator.py       # HTML/PDF/JSON 리포트 생성
└── .tmp/                          # 스캔 중간 결과 (재생성 가능)
```

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에 실제 값 입력

# 3. 스캔 실행 예시 (스캔 ID = abc123, 도메인 = ecommerce)
SCAN_ID=abc123
DOMAIN=ecommerce
SOURCE=.tmp/scan_abc123/

python tools/infra/file_extractor.py --input my_project.zip --output $SOURCE
python tools/scanner/sast_runner.py --detect-stack --path $SOURCE
python tools/scanner/domain_rule_engine.py --domain $DOMAIN --path $SOURCE
python tools/scanner/sast_runner.py --path $SOURCE --output $SOURCE/sast.sarif
python tools/scanner/sca_runner.py --path $SOURCE --output $SOURCE/sca.json
python tools/scanner/secret_scanner.py --path $SOURCE --output $SOURCE/secrets.json
python tools/report/score_calculator.py --domain $DOMAIN \
    --sast-result $SOURCE/sast.sarif \
    --sca-result $SOURCE/sca.json \
    --secret-result $SOURCE/secrets.json
```

## 지원 도메인

| 도메인 | 적용 규제 |
|--------|----------|
| ecommerce (이커머스) | PCI DSS, GDPR, 전자상거래법 |
| game (게임) | COPPA, GDPR |
| platform (플랫폼/SaaS) | SOC2, GDPR, CCPA |
| healthcare (헬스케어) | HIPAA, 개인정보보호법 |
| fintech (핀테크) | PCI DSS, 전자금융거래법 |
| education (교육) | FERPA, COPPA |

## 보안 원칙

- 사용자 소스코드는 샌드박스 내에서만 실행
- 모든 API 키/시크릿은 `.env`에만 저장
- 스캔 결과는 S3 서버사이드 암호화(AES-256) 저장
- 사용자 코드는 학습 데이터로 수집하지 않음
