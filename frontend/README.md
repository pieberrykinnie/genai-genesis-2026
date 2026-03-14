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
NEXT_PUBLIC_MAPTILER_API_KEY=
NEXT_PUBLIC_USE_MAPTILER_TILES=false
```

Notes:

1. Map tiles default to OpenStreetMap (no key required).
2. Set `NEXT_PUBLIC_USE_MAPTILER_TILES=true` to prefer MapTiler tiles.
3. Keep `NEXT_PUBLIC_MAPTILER_API_KEY` set when MapTiler tiles are enabled.

The app posts proposal payloads to Next.js API routes and proxies to the FastAPI backend:

- `POST /api/assess`
- `POST /api/assess/stream`
