## Live API
https://ai-news-api-640738486923.europe-west1.run.app/docs

## Rate limiting
`POST /ask/` is public and unauthenticated, and each call spends OpenAI credits
(one embedding call plus one `gpt-4o-mini` call), so it's rate-limited to
**10 requests/minute per client IP** via [slowapi](https://github.com/laurentS/slowapi).
Exceeding the limit returns `429 Too Many Requests`. See `app/api/rate_limit.py`.