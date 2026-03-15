"use client";

import { FormEvent, Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import dynamic from "next/dynamic";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  CloudUpload,
  FileCheck,
  Landmark,
  Loader2,
  MapPin,
  ShieldCheck,
  UserRound,
  XCircle,
  Zap,
  Droplets,
  TrendingUp,
  BarChart3,
  AlertTriangle,
  Ban,
  Clock,
  ThumbsUp,
} from "lucide-react";

import { BlurFade } from "@/components/magicui/blur-fade";
import { Button } from "@/components/ui/button";
import type {
  DataCentreProposal,
  ImpactAssessment,
  MemoJobResultResponse,
  MemoJobStatusResponse,
  MemoJobSubmitResponse,
  StreamEvent,
} from "@/types/assessment";

/* ── Map (dynamic, SSR-off) ──────────────────────────────── */
const MAPTILER_KEY = process.env.NEXT_PUBLIC_MAPTILER_API_KEY;
const LocationContextMap = dynamic(
  () => import("@/components/location-context-map").then((mod) => mod.LocationContextMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center text-sm text-slate-400">Loading map…</div>
    ),
  },
);

/* ── Demo payloads (hardcoded for hackathon demo) ────────── */
const PDF_DEMO_PROPOSAL: DataCentreProposal = {
  address: "Indus, Rocky View County, Alberta",
  province: "AB",
  it_load_mw: 1200,
  pue: 1.245,
  wue: 0.052,
  cooling_type: "air",
  facility_type: "hyperscale",
  capex_cad: 34800,
  construction_months: 24,
  has_onsite_generation: true,
  renewable_ppa: false,
};

const MANUAL_DEFAULT_PROPOSAL: DataCentreProposal = {
  address: "Brockville, Ontario",
  province: "ON",
  it_load_mw: 240,
  pue: 1.31,
  wue: 0.029,
  cooling_type: "hybrid",
  facility_type: "colocation",
  capex_cad: 5400,
  construction_months: 18,
  has_onsite_generation: false,
  renewable_ppa: true,
};

/* ── Types ───────────────────────────────────────────────── */
type StepId = 1 | 2 | 3 | 4;
type Persona = "citizen" | "councillor";
type MemoState = "idle" | "queued" | "running" | "ready" | "failed";
type IntakeMode = "upload" | "manual";
type ExtractParamKey = keyof DataCentreProposal;

const PARAM_EXTRACTION_SEQUENCE: { key: ExtractParamKey; label: string; delayMs: number }[] = [
  { key: "address", label: "Location", delayMs: 420 },
  { key: "province", label: "Province", delayMs: 300 },
  { key: "it_load_mw", label: "IT Load", delayMs: 560 },
  { key: "pue", label: "PUE", delayMs: 350 },
  { key: "wue", label: "WUE", delayMs: 340 },
  { key: "cooling_type", label: "Cooling", delayMs: 460 },
  { key: "facility_type", label: "Facility Type", delayMs: 430 },
  { key: "capex_cad", label: "CAPEX", delayMs: 520 },
  { key: "construction_months", label: "Construction", delayMs: 480 },
  { key: "has_onsite_generation", label: "On-site generation", delayMs: 320 },
  { key: "renewable_ppa", label: "Renewable PPA", delayMs: 310 },
];

const ALL_PARAM_KEYS = PARAM_EXTRACTION_SEQUENCE.map((item) => item.key);

const STEPS: { id: StepId; label: string; icon: React.ReactNode }[] = [
  { id: 1, label: "Proposal Intake", icon: <CloudUpload className="size-3.5" /> },
  { id: 2, label: "Location Context", icon: <MapPin className="size-3.5" /> },
  { id: 3, label: "Impact Results", icon: <BarChart3 className="size-3.5" /> },
  { id: 4, label: "Decision Brief", icon: <ShieldCheck className="size-3.5" /> },
];

/* ── SSE stage labels ────────────────────────────────────── */
const STAGE_LABELS: Record<string, string> = {
  starting: "Initializing…",
  proposal_ingest: "Ingesting proposal…",
  fetching_public_data: "Fetching public datasets…",
  running_calculations: "Running impact calculations…",
  running_grid_model: "Running ML grid strain model…",
  running_site_fit_model: "Evaluating site fit…",
  selecting_policy: "Selecting policy framework…",
  railtracks_workflow: "Running Railtracks AI workflow…",
  writing_memo: "Generating council memo…",
  complete: "Assessment complete",
  error: "Error occurred",
};

/* ════════════════════════════════════════════════════════════
   MAIN PAGE COMPONENT
   ════════════════════════════════════════════════════════════ */
export default function Home() {
  /* ── Core state ──────────────────────────────────────────── */
  const [proposal, setProposal] = useState<DataCentreProposal | null>(null);
  const [assessment, setAssessment] = useState<ImpactAssessment | null>(null);
  const [progress, setProgress] = useState<StreamEvent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<StepId>(1);
  const [persona, setPersona] = useState<Persona>("citizen");
  const [intakeMode, setIntakeMode] = useState<IntakeMode>("upload");

  /* ── File upload state ───────────────────────────────────── */
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [fieldsRevealed, setFieldsRevealed] = useState(false);
  const [processingParamLabel, setProcessingParamLabel] = useState<string | null>(null);
  const [revealedParamKeys, setRevealedParamKeys] = useState<ExtractParamKey[]>([]);
  const [autofillPreview, setAutofillPreview] = useState<Partial<DataCentreProposal>>({});
  const [lastFilledParamKey, setLastFilledParamKey] = useState<ExtractParamKey | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const extractionRunIdRef = useRef(0);

  /* ── Memo state ──────────────────────────────────────────── */
  const [memoState, setMemoState] = useState<MemoState>("idle");
  const [memoJobId, setMemoJobId] = useState<string | null>(null);
  const [memoError, setMemoError] = useState<string | null>(null);

  const unlockedSteps = useMemo(() => {
    return { 1: true, 2: Boolean(assessment), 3: Boolean(assessment), 4: Boolean(assessment) } as const;
  }, [assessment]);

  const canGoNext = currentStep < 4 && unlockedSteps[(currentStep + 1) as StepId];
  const allParamsReady = intakeMode === "manual"
    ? Boolean(proposal)
    : PARAM_EXTRACTION_SEQUENCE.every((item) => revealedParamKeys.includes(item.key));

  const updateProposalField = useCallback(
    <K extends keyof DataCentreProposal>(key: K, value: DataCentreProposal[K]) => {
      setProposal((prev) => {
        if (!prev) return prev;
        return { ...prev, [key]: value };
      });
    },
    [],
  );

  const switchIntakeMode = useCallback((nextMode: IntakeMode) => {
    extractionRunIdRef.current += 1;
    setIntakeMode(nextMode);
    setCurrentStep(1);
    setAssessment(null);
    setProgress(null);
    setError(null);
    setLastFilledParamKey(null);

    if (nextMode === "manual") {
      setUploadedFileName(null);
      setProcessingParamLabel(null);
      setAutofillPreview({});
      setProposal(MANUAL_DEFAULT_PROPOSAL);
      setFieldsRevealed(true);
      setRevealedParamKeys(ALL_PARAM_KEYS);
      return;
    }

    setProposal(null);
    setFieldsRevealed(false);
    setRevealedParamKeys([]);
    setAutofillPreview({});
    setProcessingParamLabel(null);
    setUploadedFileName(null);
  }, []);

  /* ── File drop handler ───────────────────────────────────── */
  const handleFileAccepted = useCallback(async (file: File) => {
    const runId = extractionRunIdRef.current + 1;
    extractionRunIdRef.current = runId;

    setIntakeMode("upload");
    setUploadedFileName(file.name);
    setProposal(null);
    setAssessment(null);
    setProgress(null);
    setError(null);
    setCurrentStep(1);
    setFieldsRevealed(true);
    setProcessingParamLabel("Initializing extraction");
    setRevealedParamKeys([]);
    setAutofillPreview({});
    setLastFilledParamKey(null);

    await sleep(280);

    for (const item of PARAM_EXTRACTION_SEQUENCE) {
      if (extractionRunIdRef.current !== runId) return;
      setProcessingParamLabel(`Extracting ${item.label}`);
      await sleep(item.delayMs);
      if (extractionRunIdRef.current !== runId) return;
      setAutofillPreview((prev) => ({ ...prev, [item.key]: PDF_DEMO_PROPOSAL[item.key] }));
      setRevealedParamKeys((prev) => (prev.includes(item.key) ? prev : [...prev, item.key]));
      setLastFilledParamKey(item.key);
      window.setTimeout(() => {
        setLastFilledParamKey((prev) => (prev === item.key ? null : prev));
      }, 450);
    }

    if (extractionRunIdRef.current === runId) {
      setProposal(PDF_DEMO_PROPOSAL);
      setProcessingParamLabel(null);
    }
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        void handleFileAccepted(file);
      }
    },
    [handleFileAccepted],
  );

  const onFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        void handleFileAccepted(file);
      }
    },
    [handleFileAccepted],
  );

  /* ── Assessment submission ───────────────────────────────── */
  const onSubmitAssessment = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!proposal || !allParamsReady) return;

    setLoading(true);
    setError(null);
    setAssessment(null);
    setMemoState("idle");
    setMemoJobId(null);
    setMemoError(null);
    setProgress({ stage: "starting", pct: 0 });

    const submittedProposal: DataCentreProposal = { ...proposal };

    try {
      const res = await fetch("/api/assess/stream", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ ...submittedProposal, defer_memo: true }),
      });

      if (!res.ok || !res.body) {
        const msg = await res.text();
        throw new Error(msg || "Unable to start assessment stream.");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";

        for (const chunk of chunks) {
          const line = chunk.trim();
          if (!line.startsWith("data:")) continue;
          const payloadText = line.slice(5).trim();
          if (!payloadText) continue;

          const evt = JSON.parse(payloadText) as StreamEvent;
          setProgress(evt);

          if (evt.stage === "error") {
            throw new Error(typeof evt.error === "string" ? evt.error : JSON.stringify(evt.error));
          }

          if (evt.stage === "complete" && evt.result) {
            setAssessment(evt.result);
            setCurrentStep(2);
            void startMemoJob(submittedProposal);
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown assessment error.");
    } finally {
      setLoading(false);
    }
  };

  /* ── Memo job polling ────────────────────────────────────── */
  const startMemoJob = async (payload: DataCentreProposal) => {
    setMemoState("queued");
    setMemoError(null);
    try {
      const submitRes = await fetch("/api/memo-jobs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!submitRes.ok) {
        const txt = await submitRes.text();
        throw new Error(txt || "Unable to queue memo generation.");
      }

      const submitData = (await submitRes.json()) as MemoJobSubmitResponse;
      if (!submitData.job_id) throw new Error("memo_job_id_missing");

      setMemoJobId(submitData.job_id);
      setMemoState(submitData.status === "running" ? "running" : "queued");
      await pollMemoJob(submitData.job_id);
    } catch (err) {
      setMemoState("failed");
      setMemoError(err instanceof Error ? err.message : "Memo job failed.");
    }
  };

  const pollMemoJob = async (jobId: string) => {
    for (let i = 0; i < 90; i += 1) {
      await sleep(2000);
      const statusRes = await fetch(`/api/memo-jobs/${jobId}`, { cache: "no-store" });
      if (!statusRes.ok) continue;

      const statusData = (await statusRes.json()) as MemoJobStatusResponse;
      if (statusData.status === "queued") { setMemoState("queued"); continue; }
      if (statusData.status === "running") { setMemoState("running"); continue; }
      if (statusData.status === "failed") {
        setMemoState("failed");
        setMemoError(statusData.error ?? "Memo generation failed.");
        return;
      }

      if (statusData.status === "succeeded") {
        const resultRes = await fetch(`/api/memo-jobs/${jobId}/result`, { cache: "no-store" });
        if (!resultRes.ok) {
          setMemoState("failed");
          setMemoError("Memo completed but result retrieval failed.");
          return;
        }

        const resultData = (await resultRes.json()) as MemoJobResultResponse;
        const result = resultData.result;

        setAssessment((prev) => {
          if (!prev) return prev;
          const fullFromJob = result.assessment;
          const mergedMemo = result.memo ?? fullFromJob?.memo ?? prev.memo;
          const mergedNarrative = result.report_narrative ?? fullFromJob?.report_narrative ?? prev.report_narrative;
          const mergedMethodology = {
            ...(prev.methodology ?? {}),
            ...((fullFromJob?.methodology as Record<string, unknown> | undefined) ?? {}),
            ...(result.methodology ?? {}),
            memo_deferred: false,
          };
          return { ...prev, memo: mergedMemo, report_narrative: mergedNarrative, methodology: mergedMethodology };
        });

        setMemoState("ready");
        setMemoError(null);
        return;
      }
    }

    setMemoState("failed");
    setMemoError("Memo generation timed out. Core assessment is still available.");
  };

  /* ════════════════════════════════════════════════════════════
     RENDER
     ════════════════════════════════════════════════════════════ */
  return (
    <main className="min-h-screen px-4 py-5 md:px-8 md:py-6">
      <div className="mx-auto w-full max-w-6xl">
        {/* ── Header ─────────────────────────────────────── */}
        <header className="hero-panel rounded-2xl px-6 py-5 md:px-8 md:py-6">
          <div className="flex items-center">
            <img
              src="/clearsite_logo.png"
              alt="ClearSite: AI-Powered Data Centre Impact Assessment"
              className="h-24 w-auto object-contain md:h-28"
            />
          </div>
          <p className="mt-4 max-w-4xl text-sm leading-7 text-slate-600 md:text-base">
            Quantified environmental, economic, and sociological impact analysis for proposed Canadian data centres — built for residents and city councils.
          </p>
        </header>

        {/* ── Step indicator ──────────────────────────────── */}
        <nav className="mt-5 flex items-center rounded-xl glass-strong px-4 py-3" aria-label="Assessment steps">
          {STEPS.map((step, idx) => {
            const active = currentStep === step.id;
            const complete = step.id < currentStep && unlockedSteps[step.id];
            const unlocked = unlockedSteps[step.id];
            return (
              <Fragment key={step.id}>
                <button
                  type="button"
                  disabled={!unlocked}
                  onClick={() => unlocked && setCurrentStep(step.id)}
                  className={`flex min-w-0 flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold transition-all ${
                    active
                      ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/20"
                      : complete
                        ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                        : unlocked
                          ? "text-slate-500 hover:bg-slate-100"
                          : "cursor-not-allowed text-slate-300"
                  }`}
                >
                  {complete ? <CheckCircle2 className="size-3.5" /> : step.icon}
                  <span className="hidden sm:inline">{step.label}</span>
                  <span className="sm:hidden">{step.id}</span>
                </button>
                {idx < STEPS.length - 1 && (
                  <div className={`mx-2 h-[2px] w-8 shrink-0 md:w-14 ${complete ? "bg-emerald-600" : "bg-emerald-500/15"}`} />
                )}
              </Fragment>
            );
          })}
        </nav>

        {/* ── Content area ────────────────────────────────── */}
        <div className="mt-5">
          <BlurFade key={currentStep} className="glass-strong rounded-2xl p-5 md:p-7">
            {/* ═══ STEP 1: PROPOSAL INTAKE ═══ */}
            {currentStep === 1 && (
              <section className="animate-fade-in">
                <SectionHeader
                  title="Proposal Intake"
                  subtitle="Upload a proposal PDF or enter parameters manually to begin the impact assessment."
                />

                <div className="mt-5 inline-flex rounded-xl border border-emerald-200/60 bg-emerald-50/70 p-1">
                  <button
                    type="button"
                    onClick={() => switchIntakeMode("upload")}
                    className={`rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${
                      intakeMode === "upload" ? "bg-emerald-600 text-white" : "text-emerald-700 hover:bg-emerald-100"
                    }`}
                  >
                    Upload PDF
                  </button>
                  <button
                    type="button"
                    onClick={() => switchIntakeMode("manual")}
                    className={`rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${
                      intakeMode === "manual" ? "bg-emerald-600 text-white" : "text-emerald-700 hover:bg-emerald-100"
                    }`}
                  >
                    Manual Entry
                  </button>
                </div>

                {/* Drop zone */}
                {intakeMode === "upload" && !uploadedFileName && (
                  <div
                    className={`drop-zone mt-5 flex flex-col items-center justify-center px-6 py-14 text-center ${
                      dragOver ? "drag-over" : ""
                    }`}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={onDrop}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <div className="rounded-2xl bg-emerald-50 p-4">
                      <CloudUpload className="size-10 text-emerald-500" />
                    </div>
                    <p className="mt-4 text-base font-semibold text-slate-800">
                      Drop your proposal PDF here
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      or click to browse files
                    </p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="application/pdf"
                      onChange={onFileInput}
                      className="hidden"
                    />
                  </div>
                )}

                {/* File accepted */}
                {intakeMode === "upload" && uploadedFileName && (
                  <div className="mt-5 animate-scale-in">
                    <div className="flex items-center gap-3 rounded-xl bg-emerald-50/80 border border-emerald-200/50 px-4 py-3">
                      {processingParamLabel ? (
                        <Loader2 className="size-5 animate-spin text-emerald-600" />
                      ) : (
                        <FileCheck className="size-5 text-emerald-600" />
                      )}
                      <div>
                        <p className="text-sm font-semibold text-emerald-800">{uploadedFileName}</p>
                        <p className="text-xs text-emerald-600">
                          {processingParamLabel
                            ? `${processingParamLabel}…`
                            : "Proposal parameters extracted successfully"}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Extracted fields */}
                {intakeMode === "upload" && fieldsRevealed && (
                  <div className="mt-5 space-y-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Live Extraction Preview
                    </p>
                    <p className="text-xs text-slate-500">
                      {allParamsReady
                        ? "All proposal parameters ready for assessment."
                        : `Processed ${revealedParamKeys.length}/${PARAM_EXTRACTION_SEQUENCE.length} parameters`}
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      <ParamCard
                        label="Location"
                        value={String(autofillPreview.address ?? "")}
                        ready={revealedParamKeys.includes("address")}
                        flash={lastFilledParamKey === "address"}
                      />
                      <ParamCard
                        label="Province"
                        value={String(autofillPreview.province ?? "")}
                        ready={revealedParamKeys.includes("province")}
                        flash={lastFilledParamKey === "province"}
                      />
                      <ParamCard
                        label="IT Load"
                        value={`${Number(autofillPreview.it_load_mw ?? 0).toLocaleString()} MW`}
                        ready={revealedParamKeys.includes("it_load_mw")}
                        flash={lastFilledParamKey === "it_load_mw"}
                      />
                      <ParamCard
                        label="PUE"
                        value={Number(autofillPreview.pue ?? 0).toString()}
                        ready={revealedParamKeys.includes("pue")}
                        flash={lastFilledParamKey === "pue"}
                      />
                      <ParamCard
                        label="WUE"
                        value={Number(autofillPreview.wue ?? 0).toString()}
                        ready={revealedParamKeys.includes("wue")}
                        flash={lastFilledParamKey === "wue"}
                      />
                      <ParamCard
                        label="Cooling"
                        value={String(autofillPreview.cooling_type ?? "").replace("_", " ")}
                        ready={revealedParamKeys.includes("cooling_type")}
                        flash={lastFilledParamKey === "cooling_type"}
                      />
                      <ParamCard
                        label="Facility Type"
                        value={String(autofillPreview.facility_type ?? "")}
                        ready={revealedParamKeys.includes("facility_type")}
                        flash={lastFilledParamKey === "facility_type"}
                      />
                      <ParamCard
                        label="CAPEX"
                        value={`$${Number(autofillPreview.capex_cad ?? 0).toLocaleString()}M CAD`}
                        ready={revealedParamKeys.includes("capex_cad")}
                        flash={lastFilledParamKey === "capex_cad"}
                      />
                      <ParamCard
                        label="Construction"
                        value={`${Number(autofillPreview.construction_months ?? 0)} months`}
                        ready={revealedParamKeys.includes("construction_months")}
                        flash={lastFilledParamKey === "construction_months"}
                      />
                    </div>

                    <div className="flex flex-wrap gap-3 animate-fade-in-up">
                      <ParamBadge
                        label="On-site generation"
                        active={Boolean(autofillPreview.has_onsite_generation)}
                        ready={revealedParamKeys.includes("has_onsite_generation")}
                      />
                      <ParamBadge
                        label="Renewable PPA"
                        active={Boolean(autofillPreview.renewable_ppa)}
                        ready={revealedParamKeys.includes("renewable_ppa")}
                      />
                    </div>

                    {/* Run assessment CTA */}
                    <form onSubmit={onSubmitAssessment} className="pt-2 animate-fade-in-up">
                      <button
                        type="submit"
                        disabled={loading || !allParamsReady}
                        className="group relative w-full overflow-hidden rounded-xl bg-emerald-600 px-6 py-4 text-base font-bold text-white shadow-lg shadow-emerald-600/25 transition-all hover:bg-emerald-700 hover:shadow-emerald-600/35 disabled:opacity-70 disabled:cursor-not-allowed md:w-auto md:min-w-[280px]"
                      >
                        <span className="relative z-10 flex items-center justify-center gap-2">
                          {loading ? (
                            <>
                              <Loader2 className="size-5 animate-spin" />
                              Running assessment…
                            </>
                          ) : !allParamsReady ? (
                            <>
                              <Loader2 className="size-5 animate-spin" />
                              Finalizing parameter extraction…
                            </>
                          ) : (
                            <>
                              <Zap className="size-5" />
                              Run Impact Assessment
                            </>
                          )}
                        </span>
                      </button>
                    </form>
                  </div>
                )}

                {intakeMode === "manual" && proposal && (
                  <div className="mt-5 space-y-4 animate-fade-in-up">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Manual Parameters
                    </p>
                    <p className="text-xs text-slate-500">
                      Default values are prefilled and can be edited before running assessment.
                    </p>

                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      <label className="space-y-1 text-xs font-semibold text-slate-500">
                        Address
                        <input
                          className="field"
                          value={proposal.address}
                          onChange={(e) => updateProposalField("address", e.target.value)}
                        />
                      </label>

                      <label className="space-y-1 text-xs font-semibold text-slate-500">
                        Province
                        <select
                          className="field"
                          value={proposal.province}
                          onChange={(e) => updateProposalField("province", e.target.value as DataCentreProposal["province"])}
                        >
                          {(["ON", "AB", "BC", "QC", "MB", "SK", "NS", "NB", "NL", "PE"] as const).map((p) => (
                            <option key={p} value={p}>{p}</option>
                          ))}
                        </select>
                      </label>

                      <label className="space-y-1 text-xs font-semibold text-slate-500">
                        IT Load (MW)
                        <input
                          className="field"
                          type="number"
                          value={proposal.it_load_mw}
                          onChange={(e) => updateProposalField("it_load_mw", Number(e.target.value) || 0)}
                        />
                      </label>

                      <label className="space-y-1 text-xs font-semibold text-slate-500">
                        PUE
                        <input
                          className="field"
                          type="number"
                          step="0.001"
                          value={proposal.pue}
                          onChange={(e) => updateProposalField("pue", Number(e.target.value) || 0)}
                        />
                      </label>

                      <label className="space-y-1 text-xs font-semibold text-slate-500">
                        WUE
                        <input
                          className="field"
                          type="number"
                          step="0.001"
                          value={proposal.wue}
                          onChange={(e) => updateProposalField("wue", Number(e.target.value) || 0)}
                        />
                      </label>

                      <label className="space-y-1 text-xs font-semibold text-slate-500">
                        Cooling Type
                        <select
                          className="field"
                          value={proposal.cooling_type}
                          onChange={(e) => updateProposalField("cooling_type", e.target.value as DataCentreProposal["cooling_type"])}
                        >
                          <option value="air">air</option>
                          <option value="evaporative">evaporative</option>
                          <option value="liquid_immersion">liquid immersion</option>
                          <option value="hybrid">hybrid</option>
                        </select>
                      </label>

                      <label className="space-y-1 text-xs font-semibold text-slate-500">
                        Facility Type
                        <select
                          className="field"
                          value={proposal.facility_type}
                          onChange={(e) => updateProposalField("facility_type", e.target.value as DataCentreProposal["facility_type"])}
                        >
                          <option value="hyperscale">hyperscale</option>
                          <option value="enterprise">enterprise</option>
                          <option value="colocation">colocation</option>
                        </select>
                      </label>

                      <label className="space-y-1 text-xs font-semibold text-slate-500">
                        CAPEX (CAD millions)
                        <input
                          className="field"
                          type="number"
                          value={proposal.capex_cad}
                          onChange={(e) => updateProposalField("capex_cad", Number(e.target.value) || 0)}
                        />
                      </label>

                      <label className="space-y-1 text-xs font-semibold text-slate-500">
                        Construction Months
                        <input
                          className="field"
                          type="number"
                          value={proposal.construction_months}
                          onChange={(e) => updateProposalField("construction_months", Number(e.target.value) || 0)}
                        />
                      </label>
                    </div>

                    <div className="flex flex-wrap gap-5 text-sm text-slate-600">
                      <label className="inline-flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={proposal.has_onsite_generation}
                          onChange={(e) => updateProposalField("has_onsite_generation", e.target.checked)}
                        />
                        On-site generation
                      </label>
                      <label className="inline-flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={proposal.renewable_ppa}
                          onChange={(e) => updateProposalField("renewable_ppa", e.target.checked)}
                        />
                        Renewable PPA
                      </label>
                    </div>

                    <form onSubmit={onSubmitAssessment} className="pt-2">
                      <button
                        type="submit"
                        disabled={loading}
                        className="group relative w-full overflow-hidden rounded-xl bg-emerald-600 px-6 py-4 text-base font-bold text-white shadow-lg shadow-emerald-600/25 transition-all hover:bg-emerald-700 hover:shadow-emerald-600/35 disabled:opacity-70 disabled:cursor-not-allowed md:w-auto md:min-w-[280px]"
                      >
                        <span className="relative z-10 flex items-center justify-center gap-2">
                          {loading ? (
                            <>
                              <Loader2 className="size-5 animate-spin" />
                              Running assessment…
                            </>
                          ) : (
                            <>
                              <Zap className="size-5" />
                              Run Impact Assessment
                            </>
                          )}
                        </span>
                      </button>
                    </form>
                  </div>
                )}

                {/* Progress */}
                {progress && loading && (
                  <ProgressPanel progress={progress} />
                )}
                {error && <ErrorBanner text={error} />}
              </section>
            )}

            {/* ═══ STEP 2: LOCATION CONTEXT ═══ */}
            {currentStep === 2 && (
              <section className="animate-fade-in">
                <SectionHeader
                  title="Location Context"
                  subtitle="Site location, local pressure indicators, and environmental baseline."
                />
                {!assessment ? (
                  <EmptyState text="Run the assessment first to view location context." />
                ) : (
                  <div className="mt-5 space-y-5">
                    {/* Map */}
                    <div className="map-shell overflow-hidden rounded-2xl border border-slate-200/50 shadow-sm">
                      <LocationContextMap
                        lat={assessment.location.lat}
                        lng={assessment.location.lng}
                        apiKey={MAPTILER_KEY}
                        noiseRadiusM={assessment.sociological.estimated_noise_radius_m}
                        waterSharePct={assessment.environmental.pct_of_municipal_daily_supply}
                        gridStrainProb={assessment.grid_strain.strain_probability}
                        populationInNoiseZone={assessment.sociological.residential_population_in_noise_zone}
                        firstNationDistanceKm={assessment.sociological.nearest_first_nation_km}
                        municipality={assessment.location.municipality}
                        province={assessment.location.province}
                      />
                    </div>
                    <p className="text-sm text-slate-500">
                      <MapPin className="mr-1 inline size-3.5 text-emerald-600" />
                      {assessment.location.municipality}, {assessment.location.province} — {assessment.location.lat.toFixed(4)}°N, {assessment.location.lng.toFixed(4)}°W
                    </p>

                    {/* Gauge cards */}
                    <div className="grid gap-4 md:grid-cols-3">
                      <GaugeCard
                        title="Water-Share Pressure"
                        icon={<Droplets className="size-4" />}
                        value={`${assessment.environmental.pct_of_municipal_daily_supply.toFixed(2)}%`}
                        level={waterShareLevel(assessment.environmental.pct_of_municipal_daily_supply)}
                        widthPct={Math.min(100, assessment.environmental.pct_of_municipal_daily_supply * 8)}
                        description={waterShareMessage(assessment.environmental.pct_of_municipal_daily_supply)}
                      />
                      <GaugeCard
                        title="Grid Strain Signal"
                        icon={<Zap className="size-4" />}
                        value={toPct(assessment.grid_strain.strain_probability)}
                        level={gridLevel(assessment.grid_strain.strain_probability)}
                        widthPct={Math.min(100, assessment.grid_strain.strain_probability * 100)}
                        description={gridImplication(assessment.grid_strain)}
                      />
                      <div className="glass rounded-xl p-4">
                        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                          <AlertTriangle className="size-4" />
                          Acoustic Radius
                        </div>
                        <p className="mt-2 text-2xl font-bold text-slate-800">
                          {typeof assessment.sociological.estimated_noise_radius_m === "number"
                            ? `${assessment.sociological.estimated_noise_radius_m.toFixed(0)} m`
                            : "Unavailable"}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          Screening radius for noise-management review.
                        </p>
                      </div>
                    </div>

                  </div>
                )}
              </section>
            )}

            {/* ═══ STEP 3: IMPACT RESULTS ═══ */}
            {currentStep === 3 && (
              <section className="animate-fade-in">
                <SectionHeader
                  title="Impact Results"
                  subtitle="Quantified environmental, economic, and grid impact with plain-language interpretation."
                />
                {!assessment ? (
                  <EmptyState text="Run the assessment first to view impact results." />
                ) : (
                  <div className="mt-5 space-y-5">
                    {/* Impact domain cards */}
                    <div className="grid gap-4 md:grid-cols-3">
                      <ImpactDomainCard
                        title="Environmental"
                        rag={assessment.environmental.carbon_score}
                        metrics={[
                          { label: "Annual CO₂", value: `${assessment.environmental.annual_carbon_tonnes.toLocaleString()} t` },
                          { label: "Daily water", value: `${assessment.environmental.total_water_litres_per_day.toLocaleString()} L` },
                          { label: "Municipal supply share", value: `${assessment.environmental.pct_of_municipal_daily_supply.toFixed(2)}%` },
                        ]}
                        icon={<Droplets className="size-5" />}
                      />
                      <ImpactDomainCard
                        title="Economic"
                        rag={assessment.economic.fiscal_score}
                        metrics={[
                          { label: "Permanent jobs", value: assessment.economic.direct_permanent_jobs.toLocaleString() },
                          { label: "10-yr tax revenue", value: `$${assessment.economic.estimated_total_tax_revenue_10yr_cad.toLocaleString()}` },
                          { label: "10-yr net fiscal", value: `$${assessment.economic.net_fiscal_impact_10yr_cad.toLocaleString()}` },
                        ]}
                        icon={<TrendingUp className="size-5" />}
                      />
                      <ImpactDomainCard
                        title="Grid Strain"
                        rag={gridRag(assessment.grid_strain.strain_probability)}
                        metrics={[
                          { label: "Strain probability", value: toPct(assessment.grid_strain.strain_probability) },
                          { label: "Rate increase risk", value: toPct(assessment.grid_strain.rate_increase_probability) },
                          { label: "Strain level", value: assessment.grid_strain.predicted_strain_level },
                        ]}
                        icon={<Zap className="size-5" />}
                      />
                    </div>

                    {/* What this means */}
                    <div className="grid gap-4 md:grid-cols-2">
                      <MeaningCard
                        title="What this means for residents"
                        icon={<UserRound className="size-4" />}
                        points={residentMeaning(assessment)}
                      />
                      <MeaningCard
                        title="What this means for council"
                        icon={<Landmark className="size-4" />}
                        points={councilMeaning(assessment)}
                      />
                    </div>

                    {/* Methodology details */}
                    <details className="glass rounded-xl p-4 text-sm">
                      <summary className="cursor-pointer font-semibold text-slate-700 flex items-center gap-2">
                        <ChevronDown className="size-4 transition-transform [[open]>&]:rotate-180" />
                        Methodology & formulas
                      </summary>
                      <div className="mt-3 space-y-1.5 text-xs text-slate-500">
                        <p>Composite: {assessment.overall_score.summary_sentence}</p>
                        <p>Carbon: {evidenceText(assessment, "environmental", "carbon_formula")}</p>
                        <p>Water: {evidenceText(assessment, "environmental", "water_formula")}</p>
                        <p>Grid: {evidenceText(assessment, "environmental", "grid_formula")}</p>
                        <p>Jobs: {evidenceText(assessment, "economic", "jobs_formula")}</p>
                        <p>Fiscal: {evidenceText(assessment, "economic", "fiscal_formula")}</p>
                      </div>
                    </details>
                  </div>
                )}
              </section>
            )}

            {/* ═══ STEP 4: DECISION BRIEF ═══ */}
            {currentStep === 4 && (
              <section className="animate-fade-in">
                <SectionHeader
                  title="Decision Brief"
                  subtitle="Policy recommendation, action items, and AI-generated council memo."
                />
                {!assessment ? (
                  <EmptyState text="Run the assessment first to view the decision brief." />
                ) : (
                  <div className="mt-5 space-y-5">
                    {/* Verdict banner */}
                    <VerdictBanner assessment={assessment} />

                    {/* Memo status */}
                    <MemoStatusCard memoState={memoState} memoError={memoError} />

                    {/* Persona toggle */}
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant={persona === "citizen" ? "default" : "outline"}
                        onClick={() => setPersona("citizen")}
                        className={persona === "citizen" ? "bg-emerald-600 hover:bg-emerald-700" : ""}
                      >
                        <UserRound className="size-4" />
                        Citizen
                      </Button>
                      <Button
                        type="button"
                        variant={persona === "councillor" ? "default" : "outline"}
                        onClick={() => setPersona("councillor")}
                        className={persona === "councillor" ? "bg-emerald-600 hover:bg-emerald-700" : ""}
                      >
                        <Landmark className="size-4" />
                        Councillor
                      </Button>
                    </div>

                    {/* Action phase cards */}
                    <div className="grid gap-4 md:grid-cols-3">
                      <ActionPhaseCard title="Immediate actions" icon={<Zap className="size-4" />} items={phaseActions(assessment, persona).now} />
                      <ActionPhaseCard title="Before permit" icon={<Clock className="size-4" />} items={phaseActions(assessment, persona).beforePermit} />
                      <ActionPhaseCard title="Post-approval" icon={<ShieldCheck className="size-4" />} items={phaseActions(assessment, persona).postApproval} />
                    </div>

                    {/* Memo text */}
                    <details className="glass rounded-xl p-4 text-sm">
                      <summary className="cursor-pointer font-semibold text-slate-700 flex items-center gap-2">
                        <ChevronDown className="size-4 transition-transform [[open]>&]:rotate-180" />
                        Council memo &amp; policy details
                      </summary>
                      <div className="mt-3 space-y-3">
                        <p className="text-xs leading-relaxed whitespace-pre-line text-slate-600">
                          {assessment.memo?.recommendation_section || assessment.report_narrative || "Memo is not available yet."}
                        </p>
                        {assessment.negotiation_playbook.length > 0 && (
                          <div className="rounded-lg border border-slate-200/50 bg-white/50 p-3">
                            <p className="text-xs font-semibold text-slate-700">Negotiation playbook</p>
                            <ul className="mt-2 space-y-1 pl-4 list-disc text-xs text-slate-600">
                              {assessment.negotiation_playbook.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </details>
                  </div>
                )}
              </section>
            )}
          </BlurFade>
        </div>

        {/* ── Bottom nav ──────────────────────────────────── */}
        <div className="mt-4 flex items-center justify-between rounded-xl glass-strong px-4 py-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => setCurrentStep((s) => Math.max(1, s - 1) as StepId)}
            disabled={currentStep === 1}
            className="gap-1.5"
          >
            <ArrowLeft className="size-4" />
            Back
          </Button>
          <span className="text-xs font-medium text-slate-400">
            Step {currentStep} of 4
          </span>
          <Button
            type="button"
            onClick={() => setCurrentStep((s) => Math.min(4, s + 1) as StepId)}
            disabled={!canGoNext || currentStep === 4}
            className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            Next
            <ArrowRight className="size-4" />
          </Button>
        </div>
      </div>
    </main>
  );
}

/* ════════════════════════════════════════════════════════════
   SUB-COMPONENTS
   ════════════════════════════════════════════════════════════ */

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <h2 className="text-xl font-bold text-slate-800">{title}</h2>
      <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
    </div>
  );
}

function ParamCard({ label, value, ready, flash = false }: { label: string; value: string; ready: boolean; flash?: boolean }) {
  return (
    <div className={`glass rounded-xl px-4 py-3 transition-all ${ready ? "animate-fade-in-up" : "opacity-70"} ${flash ? "ring-2 ring-cyan-300/70 shadow-md shadow-cyan-200/50" : ""}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</p>
      {ready ? (
        <p className="mt-1 text-sm font-bold text-slate-800">{value}</p>
      ) : (
        <p className="mt-1 inline-flex items-center gap-1.5 text-xs font-medium text-slate-500">
          <Loader2 className="size-3.5 animate-spin" />
          Processing…
        </p>
      )}
    </div>
  );
}

function ParamBadge({ label, active, ready = true }: { label: string; active: boolean; ready?: boolean }) {
  if (!ready) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200/50 bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-500">
        <Loader2 className="size-3 animate-spin" />
        Processing {label.toLowerCase()}…
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold ${
        active
          ? "bg-emerald-50 text-emerald-700 border border-emerald-200/50"
          : "bg-slate-100 text-slate-500 border border-slate-200/50"
      }`}
    >
      {active ? <CheckCircle2 className="size-3" /> : <XCircle className="size-3" />}
      {label}
    </span>
  );
}

function ProgressPanel({ progress }: { progress: StreamEvent }) {
  const stageLabel = STAGE_LABELS[progress.stage] ?? progress.stage;
  return (
    <div className="mt-5 glass rounded-xl p-4 animate-fade-in-up">
      <div className="flex items-center justify-between text-sm">
        <span className="font-semibold text-slate-700">{stageLabel}</span>
        <span className="text-xs font-medium text-emerald-600">{progress.pct}%</span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div className="progress-fill h-full rounded-full transition-all" style={{ width: `${progress.pct}%` }} />
      </div>
    </div>
  );
}

function ErrorBanner({ text }: { text: string }) {
  return (
    <div className="mt-4 flex items-start gap-3 rounded-xl border border-rose-200/50 bg-rose-50/60 px-4 py-3 animate-scale-in">
      <XCircle className="mt-0.5 size-4 shrink-0 text-rose-500" />
      <p className="text-sm text-rose-700">{text}</p>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="mt-5 flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200/50 py-12 text-center">
      <CloudUpload className="size-8 text-slate-300" />
      <p className="mt-3 text-sm text-slate-400">{text}</p>
    </div>
  );
}

function GaugeCard({
  title,
  icon,
  value,
  level,
  widthPct,
  description,
}: {
  title: string;
  icon: React.ReactNode;
  value: string;
  level: "low" | "moderate" | "high";
  widthPct: number;
  description: string;
}) {
  const color =
    level === "low" ? "bg-emerald-500" : level === "moderate" ? "bg-amber-500" : "bg-rose-500";
  const levelColor =
    level === "low" ? "text-emerald-600" : level === "moderate" ? "text-amber-600" : "text-rose-600";

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
        {icon}
        {title}
      </div>
      <div className="mt-2 flex items-end justify-between">
        <p className="text-2xl font-bold text-slate-800">{value}</p>
        <span className={`text-xs font-bold uppercase ${levelColor}`}>{level}</span>
      </div>
      <div className="gauge-track mt-3">
        <div className={`gauge-fill ${color}`} style={{ width: `${Math.max(3, widthPct)}%` }} />
      </div>
      <p className="mt-2 text-xs leading-relaxed text-slate-500">{description}</p>
    </div>
  );
}

function ImpactDomainCard({
  title,
  rag,
  metrics,
  icon,
}: {
  title: string;
  rag: string;
  metrics: { label: string; value: string }[];
  icon: React.ReactNode;
}) {
  const ragClass = rag === "green" ? "rag-green" : rag === "red" ? "rag-red" : "rag-amber";
  const ragColor = rag === "green" ? "text-emerald-600" : rag === "red" ? "text-rose-600" : "text-amber-600";

  return (
    <div className={`rag-card rounded-xl p-4`} style={{
      background: `var(--rag-bg)`,
      border: `1px solid var(--rag-border)`,
    }}>
      <div className={`${ragClass}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={ragColor}>{icon}</span>
            <h3 className="text-sm font-bold text-slate-800">{title}</h3>
          </div>
          <span className={`text-[10px] font-bold uppercase ${ragColor} rounded-full px-2 py-0.5 bg-white/60`}>
            {rag}
          </span>
        </div>
        <div className="mt-3 space-y-2">
          {metrics.map((m) => (
            <div key={m.label} className="flex items-center justify-between text-sm">
              <span className="text-slate-500">{m.label}</span>
              <span className="font-bold text-slate-800">{m.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MeaningCard({ title, icon, points }: { title: string; icon: React.ReactNode; points: string[] }) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center gap-2">
        {icon}
        <h3 className="text-sm font-bold text-slate-700">{title}</h3>
      </div>
      <ul className="mt-3 space-y-2 pl-1">
        {points.map((point) => (
          <li key={point} className="flex gap-2 text-sm text-slate-600">
            <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-emerald-400" />
            {point}
          </li>
        ))}
      </ul>
    </div>
  );
}

function VerdictBanner({ assessment }: { assessment: ImpactAssessment }) {
  const rec = assessment.policy_decision?.recommendation ?? "review";
  const verdictMap: Record<string, { className: string; icon: React.ReactNode; label: string; color: string }> = {
    reject: { className: "verdict-reject", icon: <Ban className="size-6" />, label: "Reject", color: "text-rose-600" },
    defer: { className: "verdict-defer", icon: <Clock className="size-6" />, label: "Defer", color: "text-amber-600" },
    approve_with_conditions: { className: "verdict-conditions", icon: <AlertTriangle className="size-6" />, label: "Approve with Conditions", color: "text-amber-600" },
    approve: { className: "verdict-approve", icon: <ThumbsUp className="size-6" />, label: "Approve", color: "text-emerald-600" },
  };
  const v = verdictMap[rec] ?? verdictMap.defer!;

  return (
    <div className={`${v.className} rounded-xl px-5 py-5 animate-scale-in`}>
      <div className="flex items-center gap-3">
        <span className={v.color}>{v.icon}</span>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Policy Recommendation</p>
          <p className={`text-2xl font-extrabold ${v.color}`}>{v.label}</p>
        </div>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-slate-600">
        {plainLanguageSummary(assessment)}
      </p>
    </div>
  );
}

function MemoStatusCard({ memoState, memoError }: { memoState: MemoState; memoError: string | null }) {
  return (
    <div className="glass rounded-xl px-4 py-3 flex items-center gap-3">
      {memoState === "ready" ? (
        <CheckCircle2 className="size-4 text-emerald-600" />
      ) : memoState === "failed" ? (
        <XCircle className="size-4 text-rose-500" />
      ) : (
        <Loader2 className="size-4 animate-spin text-slate-400" />
      )}
      <div>
        <p className="text-sm font-semibold text-slate-700">
          AI memo: <span className="capitalize">{memoStateLabel(memoState)}</span>
        </p>
        {memoError && <p className="text-xs text-rose-600 mt-0.5">{memoError}</p>}
        {memoState !== "ready" && memoState !== "failed" && (
          <p className="text-xs text-slate-400 mt-0.5">Continue reviewing while the AI memo generates in the background.</p>
        )}
      </div>
    </div>
  );
}

function ActionPhaseCard({ title, icon, items }: { title: string; icon: React.ReactNode; items: string[] }) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center gap-2">
        {icon}
        <h3 className="text-sm font-bold text-slate-700">{title}</h3>
      </div>
      <ul className="mt-3 space-y-2 pl-1">
        {items.map((item) => (
          <li key={item} className="flex gap-2 text-sm text-slate-600">
            <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-emerald-400" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════
   HELPER FUNCTIONS
   ════════════════════════════════════════════════════════════ */

function toPct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}

function waterShareLevel(v: number): "low" | "moderate" | "high" {
  if (v < 3) return "low";
  if (v < 10) return "moderate";
  return "high";
}

function waterShareMessage(v: number) {
  if (v < 3) return "Water demand is small relative to modeled local supply.";
  if (v < 10) return "Water demand is noticeable and may require stronger permit conditions.";
  return "Water demand is high and likely needs strict caps and mitigation terms.";
}

function gridLevel(v: number): "low" | "moderate" | "high" {
  if (v < 0.1) return "low";
  if (v < 0.25) return "moderate";
  return "high";
}

function gridRag(v: number): string {
  if (v < 0.1) return "green";
  if (v < 0.25) return "amber";
  return "red";
}

function gridImplication(grid: ImpactAssessment["grid_strain"]) {
  if (grid.strain_probability < 0.1) return "Limited expected system pressure under current assumptions.";
  if (grid.strain_probability < 0.25) return "Moderate pressure risk; utility coordination should be explicit.";
  return "High pressure risk; approvals should depend on enforceable grid mitigation commitments.";
}

function residentMeaning(a: ImpactAssessment): string[] {
  const items: string[] = [];
  if (a.environmental.pct_of_municipal_daily_supply >= 5) {
    items.push("Local water use could become a key concern, especially in dry periods.");
  } else {
    items.push("Water-demand pressure appears manageable under current assumptions.");
  }
  if (a.grid_strain.strain_probability >= 0.2) {
    items.push("There is a meaningful chance of grid pressure, so power-rate questions are valid.");
  } else {
    items.push("Grid-pressure risk appears low to moderate in this scenario.");
  }
  items.push(`Estimated people in the modeled noise influence area: ${a.sociological.residential_population_in_noise_zone.toLocaleString()}.`);
  return items;
}

function councilMeaning(a: ImpactAssessment): string[] {
  const items: string[] = [];
  items.push(`Policy recommendation currently trends to: ${(a.policy_decision?.recommendation ?? "unknown").replaceAll("_", " ")}.`);
  items.push(`Net 10-year fiscal estimate: $${a.economic.net_fiscal_impact_10yr_cad.toLocaleString()}.`);
  if (a.environmental.water_score === "red") {
    items.push("Use enforceable water caps, audit obligations, and clawback clauses before permit approval.");
  } else {
    items.push("Use annual reporting conditions to keep utility impacts transparent post-approval.");
  }
  return items;
}

function plainLanguageSummary(a: ImpactAssessment): string {
  const rec = (a.policy_decision?.recommendation ?? "review").replaceAll("_", " ");
  return `Current recommendation: ${rec}. This project is assessed as ${a.overall_score.composite_rag} risk overall, with the biggest sensitivities around water use, grid pressure, and operating efficiency assumptions.`;
}

function phaseActions(a: ImpactAssessment, persona: Persona) {
  if (persona === "citizen") {
    return {
      now: [
        "Ask for a plain-language summary of water, grid, and noise commitments.",
        "Request that key assumptions (IT load, PUE, WUE) are published for public review.",
      ],
      beforePermit: [
        "Ask council to require an independent technical review before final permits.",
        "Push for clear community notification and complaint channels.",
      ],
      postApproval: [
        "Track annual public reporting on water, jobs, and utility pressure.",
        "Report repeated noise or service issues through published oversight channels.",
      ],
    };
  }
  const permitActions = [...a.negotiation_playbook].slice(0, 2);
  while (permitActions.length < 2) {
    permitActions.push("Tie approval milestones to audited environmental and infrastructure commitments.");
  }
  return {
    now: [
      "Record critical assumptions in the motion and require independent validation.",
      "Align utility coordination milestones before permit issuance.",
    ],
    beforePermit: permitActions,
    postApproval: [
      "Require annual compliance reporting on water, grid, tax, and jobs outcomes.",
      "Include enforcement triggers for missed commitments.",
    ],
  };
}

function evidenceText(
  assessment: ImpactAssessment,
  section: "environmental" | "economic" | "sociological" | "grid_strain",
  key: string,
) {
  const sectionRecord = assessment.evidence_pack?.[section];
  if (!sectionRecord || typeof sectionRecord !== "object") return "unavailable";
  const value = (sectionRecord as Record<string, unknown>)[key];
  return value == null ? "unavailable" : String(value);
}

function memoStateLabel(state: MemoState) {
  switch (state) {
    case "idle": return "not started";
    case "queued": return "queued";
    case "running": return "generating";
    case "ready": return "ready";
    case "failed": return "failed";
    default: return state;
  }
}

function sleep(ms: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(() => resolve(), ms);
  });
}
