# genai-genesis-2026

## Quickstart

1. Install `pnpm`:

```bash
# macOS / Linux
curl -fsSL https://get.pnpm.io/install.sh | sh -
# Windows
npx pnpm@latest-10 dlx @pnpm/exe@latest-10 setup
```

2. Install `uv`:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

3. Install frontend dependencies:

```bash
cd frontend
pnpm install
```

4. Install backend dependencies:

```bash
cd ../backend
uv sync
```

5. Run frontend development server:

```bash
cd ../frontend
pnpm dev
```

6. Run backend development server:

```bash
cd ../backend
uv run fastapi dev
```

## Contributing

### Branching

Four layers:

1. `main` stable branch and what we will use in our final submission
1. `dev` for merging working features
1. `feat`/`fix`/`docs` branches
