# Brand Team Bot 🤖

AI 브랜딩 팀 디스코드 봇 — 4명의 전문 AI가 브랜드 작업을 도와줍니다.

| 팀원 | 역할 |
|------|------|
| ◆ Strategist | 브랜드 포지셔닝, 타겟, 컨셉 전략 |
| ▲ Copywriter | 네이밍, 태그라인, 브랜드 카피 |
| ● Director | 비주얼 방향, 컬러, 타이포, 소재 |
| ■ Reviewer | 크리틱 & 피드백 (10점 스케일) |

---

## 🚀 셋업 가이드 (처음부터 끝까지)

### Step 1. Discord 봇 만들기

1. [Discord Developer Portal](https://discord.com/developers/applications) 접속
2. **New Application** 클릭 → 이름: `Brand Team` (아무거나 OK)
3. 왼쪽 메뉴 **Bot** 클릭
4. **Reset Token** → 토큰 복사 (나중에 필요)
5. 아래로 스크롤 → **Message Content Intent** 켜기 ✅
6. 왼쪽 메뉴 **OAuth2** → **URL Generator**
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`
7. 생성된 URL로 접속해서 봇을 서버에 초대

### Step 2. Anthropic API 키 발급

1. [Anthropic Console](https://console.anthropic.com) 접속
2. API Keys → Create Key → 복사

### Step 3. Railway 배포 (무료~$5/월)

1. [Railway](https://railway.app) 가입 (GitHub 연동 추천)
2. **New Project** → **Deploy from GitHub repo**
   - 이 코드를 GitHub에 올린 후 연결
   - 또는 **Empty Project** → 수동 배포도 가능
3. **Variables** 탭에서 환경변수 추가:
   ```
   DISCORD_TOKEN=복사한_디스코드_토큰
   DISCORD_APP_ID=디스코드_앱_ID
   ANTHROPIC_API_KEY=복사한_API_키
   ```
4. **Settings** → Start Command: `npm start`
5. Deploy 클릭!

### Step 4. 슬래시 명령어 등록

Railway 배포 후, 한 번만 실행:
```bash
npm run register
```
또는 Railway의 **Execute Command** 에서 `node register-commands.js` 실행.

### Step 5. Discord 서버 채널 만들기

서버에 텍스트 채널 4개 만들기:
- `#strategist`
- `#copywriter`  
- `#director`
- `#reviewer`

이 채널에서는 **명령어 없이** 그냥 메시지 쓰면 해당 에이전트가 자동 응답!

---

## 💬 사용법

### 방법 1: 전용 채널에서 바로 대화
`#strategist` 채널에서 그냥 메시지 쓰면 Strategist가 대답.

### 방법 2: 슬래시 명령어
아무 채널에서:
```
/ask agent:strategist message:OARE 브랜드 포지셔닝 잡아줘
/ask agent:copywriter message:오피스 향 브랜드 태그라인 5개 만들어줘
```

### 방법 3: 브리프 동시 전달
```
/brief content:25-38세 직장인 타겟 프리미엄 오피스 향 브랜드. 알루미늄 패키징, 다크 럭셔리 방향.
```
→ 4명이 동시에 분석해서 각자 답변!

### 기타
```
/team   → 팀원 소개
/clear  → 대화 기록 초기화
```

---

## 📁 파일 구조

```
brand-team-bot/
├── bot.js                 ← 메인 봇
├── register-commands.js   ← 슬래시 명령어 등록 (1회만)
├── package.json
├── .env.example           ← 환경변수 템플릿
└── README.md              ← 이 파일
```

---

## 💰 비용

- **Discord**: 무료
- **Railway**: 무료 tier 있음 ($5/월 hobby plan 추천)
- **Anthropic API**: 사용량 기반 — 일반적 브랜딩 대화 기준 월 $2~5 정도

---

## ⚙️ 커스텀

### 에이전트 수정
`bot.js`의 `AGENTS` 객체에서 `system` 프롬프트를 수정하면 에이전트 성격/역할 변경 가능.

### 채널 이름 변경
`.env`에서 `CHANNEL_STRATEGIST=전략` 이런 식으로 한글 채널명도 가능.

### 대화 기록 길이
`MAX_HISTORY` 값 변경 (기본 20개 메시지).
