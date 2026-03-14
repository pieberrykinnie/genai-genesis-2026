# DataSite Impact Analyzer Frontend

## Run

```bash
pnpm install
pnpm dev
```

## Environment

Create `.env.local` from `.env.example`:

```bash
BACKEND_URL=http://127.0.0.1:8000
```

The app posts proposal payloads to Next.js API routes and proxies to the FastAPI backend:

- `POST /api/assess`
- `POST /api/assess/stream`
