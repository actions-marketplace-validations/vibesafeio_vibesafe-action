const express = require('express')
const crypto = require('crypto')
const app = express()

app.use(express.json())

// 더미값 - 실제 시크릿 아님
const DB_HOST = 'localhost'

app.get('/health', (req, res) => {
  res.json({ status: 'ok' })
})

// eval 사용 (Semgrep: dangerous-eval / code-injection)
app.post('/calculate', (req, res) => {
  const result = eval(req.body.expression)
  res.json({ result })
})

// 약한 해시 알고리즘 MD5 (Semgrep: insecure-hash)
app.post('/checksum', (req, res) => {
  const hash = crypto.createHash('md5').update(req.body.data).digest('hex')
  res.json({ hash })
})

// Math.random() 보안 토큰 생성 (Semgrep: insecure-random)
app.get('/session-token', (req, res) => {
  const token = Math.random().toString(36).slice(2) +
                Math.random().toString(36).slice(2)
  res.json({ token })
})

// 에러 메시지에 스택트레이스 노출 (정보 노출)
app.use((err, req, res, next) => {
  res.status(500).json({ error: err.message, stack: err.stack })
})

app.listen(3000)
