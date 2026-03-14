import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-background px-4">
      <h1 className="text-center text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
        GenAI Genesis 2026
      </h1>
      <Link
        href="/dashboard"
        className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Go to dashboard
      </Link>
    </div>
  );
}
