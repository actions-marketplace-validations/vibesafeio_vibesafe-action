from __future__ import annotations
#!/usr/bin/env python3
"""
tools/report/compliance_checker.py
도메인별 규제(PCI DSS, GDPR, HIPAA, COPPA 등)에 대한 준수 여부를 판정한다.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# ─── 규제별 필수 요구사항 매핑 ───────────────────────────
COMPLIANCE_REQUIREMENTS = {
    "PCI DSS": {
        "domains": ["ecommerce", "fintech"],
        "requirements": [
            {
                "id": "PCI-6.2",
                "name": "알려진 취약점 패치",
                "check": lambda vulns: not any(v["severity"] in ("critical", "high") and "dependency" in v.get("type", "") for v in vulns),
                "penalty": "최대 $100,000/월 벌금 + 카드 처리 자격 박탈",
            },
            {
                "id": "PCI-6.4",
                "name": "SQL Injection 방어",
                "check": lambda vulns: not any("sql_injection" in v.get("type", "") for v in vulns),
                "penalty": "보안 감사 의무화",
            },
            {
                "id": "PCI-3.4",
                "name": "카드 데이터 암호화",
                "check": lambda vulns: not any("missing_encryption" in v.get("type", "") for v in vulns),
                "penalty": "보안 사고 시 전액 배상 책임",
            },
            {
                "id": "PCI-6.5.1",
                "name": "하드코딩된 시크릿 금지",
                "check": lambda vulns: not any("hardcoded_secret" in v.get("type", "") for v in vulns),
                "penalty": "즉각적 감사 대상",
            },
        ],
    },
    "GDPR": {
        "domains": ["ecommerce", "game", "platform", "healthcare", "fintech", "education"],
        "requirements": [
            {
                "id": "GDPR-Art32",
                "name": "개인정보 처리 보안 조치",
                "check": lambda vulns: not any(v["severity"] == "critical" for v in vulns),
                "penalty": "전 세계 매출 4% 또는 €2000만 중 높은 금액",
            },
            {
                "id": "GDPR-Art25",
                "name": "Privacy by Design (IDOR 방어)",
                "check": lambda vulns: not any("idor" in v.get("type", "") for v in vulns),
                "penalty": "€1000만 또는 전 세계 매출 2%",
            },
        ],
    },
    "HIPAA": {
        "domains": ["healthcare"],
        "requirements": [
            {
                "id": "HIPAA-164.312(a)(2)(iv)",
                "name": "PHI 암호화",
                "check": lambda vulns: not any("missing_encryption" in v.get("type", "") for v in vulns),
                "penalty": "$100~$50,000/건, 최대 $1.9M/년",
            },
            {
                "id": "HIPAA-164.312(b)",
                "name": "감사 추적 (Audit Controls)",
                "check": lambda vulns: not any(v["severity"] in ("critical", "high") for v in vulns),
                "penalty": "민사 벌금 + 형사 기소 가능",
            },
        ],
    },
    "COPPA": {
        "domains": ["game", "education"],
        "requirements": [
            {
                "id": "COPPA-312.8",
                "name": "미성년자 데이터 보안",
                "check": lambda vulns: not any(v["severity"] in ("critical", "high") for v in vulns),
                "penalty": "$51,744/건",
            },
        ],
    },
    "SOC2": {
        "domains": ["platform"],
        "requirements": [
            {
                "id": "SOC2-CC6.1",
                "name": "접근 제어 (IDOR/BOLA 방어)",
                "check": lambda vulns: not any("idor" in v.get("type", "") or "bola" in v.get("type", "") for v in vulns),
                "penalty": "SOC2 인증 취소, 기업 고객 계약 해지",
            },
            {
                "id": "SOC2-CC6.6",
                "name": "외부 위협 방어 (XSS, Injection)",
                "check": lambda vulns: not any(v["severity"] in ("critical", "high") for v in vulns),
                "penalty": "감사 실패, 재인증 필요",
            },
        ],
    },
    "전자금융거래법": {
        "domains": ["fintech"],
        "requirements": [
            {
                "id": "전금법-21",
                "name": "전자금융 거래 보안",
                "check": lambda vulns: not any("sql_injection" in v.get("type", "") or "hardcoded_secret" in v.get("type", "") for v in vulns),
                "penalty": "5년 이하 징역 또는 3000만원 이하 벌금",
            },
        ],
    },
}


def check_compliance(domain: str, vulnerabilities: list[dict]) -> dict:
    """도메인에 해당하는 규제를 확인하고 준수 여부를 반환한다."""
    applicable_regulations = {
        reg_name: reg_data
        for reg_name, reg_data in COMPLIANCE_REQUIREMENTS.items()
        if domain in reg_data["domains"]
    }

    results = {}
    overall_compliant = True

    for reg_name, reg_data in applicable_regulations.items():
        reg_results = []
        reg_compliant = True

        for req in reg_data["requirements"]:
            try:
                compliant = req["check"](vulnerabilities)
            except Exception:
                compliant = False

            reg_results.append({
                "id": req["id"],
                "name": req["name"],
                "compliant": compliant,
                "penalty": req["penalty"] if not compliant else None,
            })

            if not compliant:
                reg_compliant = False
                overall_compliant = False

        results[reg_name] = {
            "compliant": reg_compliant,
            "requirements": reg_results,
            "pass_rate": f"{sum(1 for r in reg_results if r['compliant'])}/{len(reg_results)}",
        }

    return {
        "domain": domain,
        "overall_compliant": overall_compliant,
        "applicable_regulations": list(applicable_regulations.keys()),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="VibeSafe 규제 준수 검사기")
    parser.add_argument("--domain", required=True, help="서비스 도메인")
    parser.add_argument("--scan-results", required=True, help="통합 스캔 결과 JSON 파일")
    args = parser.parse_args()

    results_path = Path(args.scan_results)
    if not results_path.exists():
        print(json.dumps({"error": f"파일을 찾을 수 없습니다: {args.scan_results}"}))
        sys.exit(1)

    scan_data = json.loads(results_path.read_text())
    vulns = scan_data.get("vulnerabilities", [])

    result = check_compliance(args.domain, vulns)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
