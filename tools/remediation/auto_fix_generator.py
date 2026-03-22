from __future__ import annotations
#!/usr/bin/env python3
"""
tools/remediation/auto_fix_generator.py
취약점별 수정 코드(패치)와 AI 프롬프트를 생성한다.
바이브 코더가 이해할 수 있는 언어로 설명을 제공한다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic

# ─── 취약점 유형별 수정 템플릿 ───────────────────────────
FIX_TEMPLATES = {
    "sql_injection": {
        "description_simple": "사용자가 입력한 값이 바로 데이터베이스 명령어에 들어가서, 해커가 모든 데이터를 훔칠 수 있어요.",
        "ai_prompt_template": "내 코드 {file} {line}번째 줄에서 SQL 쿼리를 파라미터화된 쿼리로 변경해줘. template literal 대신 파라미터 바인딩($1, ?, :param)을 사용하도록 수정해줘.",
        "references": ["https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"],
    },
    "xss": {
        "description_simple": "사용자가 입력한 내용이 그대로 화면에 표시되어 해커가 악성 스크립트를 실행할 수 있어요.",
        "ai_prompt_template": "{file} {line}번째 줄에서 사용자 입력값을 HTML에 표시하기 전에 이스케이프 처리해줘. dangerouslySetInnerHTML 대신 안전한 렌더링 방법을 사용해줘.",
        "references": ["https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html"],
    },
    "hardcoded_secret": {
        "description_simple": "코드에 비밀번호나 API 키가 직접 적혀 있어서 코드를 보는 누구나 이 정보를 볼 수 있어요.",
        "ai_prompt_template": "{file} {line}번째 줄의 하드코딩된 값을 환경 변수로 변경해줘. process.env.VARIABLE_NAME 형태로 수정하고 .env 파일에 실제 값을 저장해줘.",
        "references": ["https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html"],
    },
    "missing_encryption": {
        "description_simple": "민감한 데이터가 암호화 없이 저장되거나 전송되어 해커가 쉽게 읽을 수 있어요.",
        "ai_prompt_template": "{file} {line}번째 줄에서 민감한 데이터를 저장하기 전에 암호화를 적용해줘. AES-256 또는 bcrypt를 사용해줘.",
        "references": ["https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html"],
    },
    "idor": {
        "description_simple": "URL이나 파라미터의 숫자를 바꾸면 다른 사람의 데이터에 접근할 수 있어요.",
        "ai_prompt_template": "{file} {line}번째 줄에서 리소스에 접근하기 전에 현재 로그인한 사용자가 해당 리소스의 소유자인지 확인하는 권한 검사를 추가해줘.",
        "references": ["https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html"],
    },
    "ssrf": {
        "description_simple": "외부 URL을 서버가 직접 요청할 때 공격자가 내부 시스템에 접근하도록 유도할 수 있어요.",
        "ai_prompt_template": "{file} {line}번째 줄에서 외부 URL 요청 전에 허용된 도메인 목록(allowlist)과 대조하는 검증을 추가해줘. 내부 IP 주소(127.0.0.1, 192.168.x.x, 10.x.x.x)는 차단해줘.",
        "references": ["https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html"],
    },
}


def generate_patch_with_ai(
    vuln: dict,
    source_code: str,
    client: anthropic.Anthropic,
) -> str | None:
    """Claude API를 사용하여 실제 패치 코드를 생성한다."""
    prompt = f"""다음 취약점에 대해 정확한 코드 패치를 생성해주세요.

취약점 유형: {vuln.get('type')}
파일: {vuln.get('file')}
라인: {vuln.get('line')}
설명: {vuln.get('description', '')}

현재 코드 (문제 있는 라인 주변):
```
{source_code}
```

다음 형식으로 unified diff 패치만 출력해주세요 (설명 없이):
--- a/{vuln.get('file')}
+++ b/{vuln.get('file')}
@@ -줄번호,컨텍스트 +줄번호,컨텍스트 @@
 (변경 없는 컨텍스트 줄)
-제거할 줄
+추가할 줄
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception:
        return None


def extract_code_context(source_path: Path, file_rel: str, line_num: int, context: int = 5) -> str:
    """취약점 주변 코드 컨텍스트를 추출한다."""
    file_path = source_path / file_rel
    if not file_path.exists():
        # 경로가 절대경로인 경우도 시도
        file_path = Path(file_rel)
    if not file_path.exists():
        return ""

    lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = max(0, line_num - context - 1)
    end = min(len(lines), line_num + context)
    return "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines[start:end], start=start))


def process_vulnerability(vuln: dict, source_path: Path, client: anthropic.Anthropic | None) -> dict:
    """단일 취약점에 대한 수정 제안을 생성한다."""
    vuln_type = vuln.get("type", "").lower()
    file_rel = vuln.get("file", "")
    line_num = vuln.get("line", 0)

    # 기본 설명 및 AI 프롬프트
    template = FIX_TEMPLATES.get(vuln_type, {
        "description_simple": "이 코드에 보안 취약점이 발견되었습니다. 개발자 도구에서 수정이 필요합니다.",
        "ai_prompt_template": "{file} {line}번째 줄의 보안 취약점을 수정해줘.",
        "references": ["https://owasp.org/www-project-top-ten/"],
    })

    ai_prompt = template["ai_prompt_template"].format(file=file_rel, line=line_num)

    # AI 패치 생성 (API 키가 있는 경우)
    patch = None
    if client:
        code_context = extract_code_context(source_path, file_rel, line_num)
        if code_context:
            patch = generate_patch_with_ai(vuln, code_context, client)

    return {
        "vuln_id": vuln.get("vuln_id", f"VULN-{hash(str(vuln)) % 10000:04d}"),
        "type": vuln_type,
        "severity": vuln.get("severity", "medium"),
        "file": file_rel,
        "line": line_num,
        "description_ko": vuln.get("description", ""),
        "description_simple": template["description_simple"],
        "patch": patch,
        "ai_prompt": ai_prompt,
        "references": template["references"],
        "patch_available": patch is not None,
    }


def main():
    parser = argparse.ArgumentParser(description="VibeSafe 자동 수정 제안 생성기")
    parser.add_argument("--scan-id", required=True, help="스캔 ID")
    parser.add_argument("--vuln-file", required=True, help="취약점 JSON 파일 경로")
    parser.add_argument("--source-path", required=True, help="소스 코드 경로")
    parser.add_argument("--output", required=True, help="패치 출력 디렉토리")
    args = parser.parse_args()

    vuln_path = Path(args.vuln_file)
    if not vuln_path.exists():
        print(json.dumps({"error": f"취약점 파일을 찾을 수 없습니다: {args.vuln_file}"}))
        sys.exit(1)

    vulnerabilities = json.loads(vuln_path.read_text())
    if isinstance(vulnerabilities, dict):
        vulnerabilities = vulnerabilities.get("vulnerabilities", [])

    source_path = Path(args.source_path)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Claude 클라이언트 초기화 (API 키가 있는 경우만)
    client = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        client = anthropic.Anthropic()

    # 우선순위 정렬 (CVSS 점수 내림차순)
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    vulnerabilities.sort(key=lambda v: severity_order.get(v.get("severity", "").lower(), 0), reverse=True)

    patches = []
    for vuln in vulnerabilities:
        fix = process_vulnerability(vuln, source_path, client)
        patches.append(fix)

        # 개별 패치 파일 저장
        patch_file = output_dir / f"{fix['vuln_id']}.json"
        patch_file.write_text(json.dumps(fix, ensure_ascii=False, indent=2))

    result = {
        "status": "ok",
        "scan_id": args.scan_id,
        "total_patches": len(patches),
        "auto_patch_available": sum(1 for p in patches if p["patch_available"]),
        "patches": patches,
    }

    (output_dir / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
