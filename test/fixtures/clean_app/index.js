const express = require('express')
const app = express()

app.use(express.json())

// 파라미터화된 쿼리 사용 (안전)
app.get('/users/:id', (req, res) => {
  const userId = parseInt(req.params.id, 10)
  if (isNaN(userId)) {
    return res.status(400).json({ error: 'Invalid user id' })
  }
  res.json({ id: userId, name: 'Alice' })
})

// 입력값 escape 처리 (안전)
app.get('/search', (req, res) => {
  const query = String(req.query.q || '').replace(/[<>"']/g, '')
  res.json({ results: [], query })
})

app.listen(3000)
