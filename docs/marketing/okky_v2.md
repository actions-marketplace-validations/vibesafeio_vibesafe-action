제목: Cursor로 만든 Flask 앱, 보안 스캐너 돌려봤더니 0점 나왔습니다

---

지난주에 Cursor로 Flask 앱 하나 만들었습니다. 로그인, 대시보드, API까지. 20분 정도 걸렸고 잘 돌아갔습니다.

그런데 문득 궁금해서 보안 스캐너를 돌려봤습니다.

**100점 만점에 0점. F등급.**

AI가 알아서 써준 코드들:

- `eval(user_input)` — 사용자가 서버에서 아무 코드나 실행 가능
- `subprocess.run(cmd, shell=True)` — 커맨드 인젝션
- `f"SELECT * FROM users WHERE id = {user_id}"` — SQL 인젝션
- JWT 시크릿이 소스코드에 `"secret123"`으로 하드코딩

전부 정상 동작합니다. 앱은 잘 돌아갑니다. 근데 아는 사람이 보면 서버 통째로 털 수 있는 코드입니다.

## 저만 그런 게 아니었습니다

GitHub에서 Lovable, Bolt, Cursor로 만든 오픈소스 프로젝트 10개를 스캔해봤습니다.

10개 중 8개에서 문제가 나왔습니다. 보안만이 아니라 접근성도요. 이미지에 alt 속성 없는 것, 폼 input에 label 없는 것, 클릭 가능한 div에 role 속성 없는 것. 이런 게 소송감입니다.

과장이 아닙니다. 미국에서 웹 접근성 소송이 2024년에만 4,000건 넘게 나왔습니다. 64%가 매출 $25M 미만 기업을 타겟했고, 합의금이 $5K~$75K입니다. AI는 이런 걸 모릅니다. 눈이 보이고 마우스를 쓰는 사용자한테만 동작하는 코드를 쓸 뿐입니다.

패턴이 항상 같습니다. AI는 "동작하는 최단 경로"를 선택하고, 최단 경로는 거의 항상 가장 안전하지 않은 경로입니다.

## 그래서 만든 것

PR 올릴 때마다 자동으로 돌아가는 GitHub Action을 만들었습니다. 보안 취약점, 접근성 위반, AI가 자주 생성하는 위험한 패턴들을 잡습니다.

YAML 파일 하나 추가하면 됩니다:

```yaml
name: VibeSafe
on: [pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: vibesafeio/vibesafe-action@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

PR에 코멘트로 뭐가 발견됐는지, 어디에 있는지, 어떻게 고치면 되는지 알려줍니다. AI 코딩 도구 쓰시면 fix 제안을 그대로 복사해서 붙여넣으면 됩니다.

## 한계

솔직하게 말씀드리면:

- 비즈니스 로직 버그는 못 잡습니다. 인증 흐름이 설계부터 잘못됐으면 패턴 매칭으론 알 수 없습니다.
- 정적 분석입니다. 코드를 읽는 거지 앱을 실행하는 게 아닙니다.
- 전부 잡지는 못합니다. AI가 반복적으로 만드는 흔한 패턴들을 잡는 겁니다.

## 공유하는 이유

저는 보안 전문가가 아닙니다. 그래서 이게 필요했습니다. 바이브 코딩하고 AI가 뭘 썼는지 안 보고 배포하고 계시다면, 최소한 뭐가 들어있는지는 알아두시는 게 좋지 않을까 싶어서 공유합니다.

레포: https://github.com/vibesafeio/vibesafe-action

무료, 오픈소스, 계정 필요 없습니다. 써보시고 뭔가 이상한 게 잡히면 알려주세요.
