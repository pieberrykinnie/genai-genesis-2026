"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Landmark,
  Loader2,
  ShieldCheck,
  Upload,
  UserRound,
  XCircle,
} from "lucide-react";

import { AnimatedGradientText } from "@/components/magicui/animated-gradient-text";
import { BlurFade } from "@/components/magicui/blur-fade";
import { ShinyButton } from "@/components/magicui/shiny-button";
import { Button } from "@/components/ui/button";
import type {
  DataCentreProposal,
  ExtractProposalResponse,
  ImpactAssessment,
  MemoJobResultResponse,
  MemoJobStatusResponse,
  MemoJobSubmitResponse,
  StreamEvent,
} from "@/types/assessment";

const MAPTILER_KEY = process.env.NEXT_PUBLIC_MAPTILER_API_KEY;

const LocationContextMap = dynamic(
  () => import("@/components/location-context-map").then((mod) => mod.LocationContextMap),
  {
    ssr: false,
    loading: () => <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading map...</div>,
  },
);

const PROVINCES: DataCentreProposal["province"][] = ["ON", "AB", "BC", "QC", "MB", "SK", "NS", "NB", "NL", "PE"];

const DEFAULT_PROPOSAL: DataCentreProposal = {
  address: "Municipal District of Greenview, Grande Prairie, Alberta",
  province: "AB",
  it_load_mw: 200,
  pue: 1.5,
  wue: 1.9,
  cooling_type: "evaporative",
  facility_type: "hyperscale",
  capex_cad: 5000,
  construction_months: 36,
  has_onsite_generation: true,
  renewable_ppa: false,
};

type StepId = 1 | 2 | 3 | 4;
type Persona = "citizen" | "councillor";
type IntakeMode = "manual" | "upload";
type MemoState = "idle" | "queued" | "running" | "ready" | "failed";
type ScenarioId = "baseline_ab" | "balanced_qc" | "beacon_high_load";

interface ScenarioPreset {
  id: ScenarioId;
  label: string;
  description: string;
  proposal: DataCentreProposal;
  expectedSignals: string[];
}

const PRESETS: ScenarioPreset[] = [
  {
    id: "baseline_ab",
    label: "Baseline AB",
    description: "Reference 200 MW Alberta profile for normal demo flow.",
    proposal: DEFAULT_PROPOSAL,
    expectedSignals: [
      "Low-to-moderate grid strain probability",
      "Water share should stay under 5%",
      "Decision is usually defer or conditional approval",
    ],
  },
  {
    id: "balanced_qc",
    label: "Balanced QC",
    description: "Lower-intensity Quebec profile to show a milder outcome.",
    proposal: {
      address: "Levis, Quebec, Canada",
      province: "QC",
      it_load_mw: 100,
      pue: 1.3,
      wue: 0.8,
      cooling_type: "liquid_immersion",
      facility_type: "enterprise",
      capex_cad: 800,
      construction_months: 24,
      has_onsite_generation: false,
      renewable_ppa: true,
    },
    expectedSignals: [
      "Lower environmental burden than high-load AB",
      "Low grid strain probability",
      "Fewer hard policy triggers",
    ],
  },
  {
    id: "beacon_high_load",
    label: "Beacon-like High Load",
    description: "Stress-case based on 4 x 300 MW (about 1200 MW) scale from the sample proposal.",
    proposal: {
      address: "Grande Prairie, Alberta, Canada",
      province: "AB",
      it_load_mw: 1200,
      pue: 1.6,
      wue: 2.2,
      cooling_type: "evaporative",
      facility_type: "hyperscale",
      capex_cad: 18000,
      construction_months: 60,
      has_onsite_generation: true,
      renewable_ppa: false,
    },
    expectedSignals: [
      "Higher water-share pressure",
      "Higher grid strain and stronger policy constraints",
      "More difficult recommendation path",
    ],
  },
];

const STEP_COPY: Record<StepId, { title: string; subtitle: string }> = {
  1: {
    title: "1. Proposal Intake",
    subtitle: "Enter project assumptions manually or upload a proposal PDF to prefill fields.",
  },
  2: {
    title: "2. Location Context",
    subtitle: "Map view plus plain-language local pressure indicators.",
  },
  3: {
    title: "3. Impact Results",
    subtitle: "Understand what the numbers mean for residents and council decisions.",
  },
  4: {
    title: "4. Decision Brief",
    subtitle: "Persona-based actions for citizens and councillors.",
  },
};

export default function Home() {
  const [proposal, setProposal] = useState<DataCentreProposal>(DEFAULT_PROPOSAL);
  const [assessment, setAssessment] = useState<ImpactAssessment | null>(null);
  const [progress, setProgress] = useState<StreamEvent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<StepId>(1);
  const [persona, setPersona] = useState<Persona>("citizen");

  const [intakeMode, setIntakeMode] = useState<IntakeMode>("manual");
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [extractionMeta, setExtractionMeta] = useState<ExtractProposalResponse["_extraction"] | null>(null);
  const [extractError, setExtractError] = useState<string | null>(null);

  const [selectedPreset, setSelectedPreset] = useState<ScenarioId>("baseline_ab");
  const [expectationSummary, setExpectationSummary] = useState<string | null>(null);

  const [memoState, setMemoState] = useState<MemoState>("idle");
  const [memoJobId, setMemoJobId] = useState<string | null>(null);
  const [memoError, setMemoError] = useState<string | null>(null);

  const unlockedSteps = useMemo(() => {
    return {
      1: true,
      2: Boolean(assessment),
      3: Boolean(assessment),
      4: Boolean(assessment),
    } as const;
  }, [assessment]);

  const canGoNext = currentStep < 4 && unlockedSteps[(currentStep + 1) as StepId];

  useEffect(() => {
    const preset = PRESETS.find((item) => item.id === selectedPreset);
    if (!preset) return;
    setProposal(preset.proposal);
    setExtractionMeta(null);
    setExtractError(null);
  }, [selectedPreset]);

  const onSubmitAssessment = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setAssessment(null);
    setExpectationSummary(null);
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
            setExpectationSummary(evaluateScenarioMatch(selectedPreset, evt.result));
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
      if (!submitData.job_id) {
        throw new Error("memo_job_id_missing");
      }

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

      if (statusData.status === "queued") {
        setMemoState("queued");
        continue;
      }
      if (statusData.status === "running") {
        setMemoState("running");
        continue;
      }
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

          return {
            ...prev,
            memo: mergedMemo,
            report_narrative: mergedNarrative,
            methodology: mergedMethodology,
          };
        });

        setMemoState("ready");
        setMemoError(null);
        return;
      }
    }

    setMemoState("failed");
    setMemoError("Memo generation timed out. Core assessment is still available.");
  };

  const onExtractFromPdf = async () => {
    if (!pdfFile) {
      setExtractError("Select a PDF file first.");
      return;
    }

    setExtracting(true);
    setExtractError(null);
    setExtractionMeta(null);

    try {
      const form = new FormData();
      form.append("file", pdfFile);

      const res = await fetch("/api/extract-proposal", {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Unable to extract proposal from PDF.");
      }

      const extracted = (await res.json()) as ExtractProposalResponse;
      const next = mergeExtractedProposal(proposal, extracted);
      setProposal(next);
      setExtractionMeta(extracted._extraction ?? null);
      setIntakeMode("manual");
    } catch (err) {
      setExtractError(err instanceof Error ? err.message : "PDF extraction failed.");
    } finally {
      setExtracting(false);
    }
  };

  return (
    <main className="min-h-screen px-4 py-6 md:px-8 md:py-8">
      <div className="mx-auto w-full max-w-6xl">
        <header className="hero-panel rounded-3xl border px-5 py-5 md:px-8 md:py-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-900/80">Data Centre Public Impact Tool</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
            Assessment <AnimatedGradientText speed={1.6}>Workspace</AnimatedGradientText>
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-700">
            Built for residents and city councils. Start with assumptions or upload a proposal PDF, then review map context, impacts, and action-ready recommendations.
          </p>
        </header>

        <div className="mt-5 grid gap-4 md:grid-cols-[260px_minmax(0,1fr)]">
          <nav className="rounded-2xl border border-slate-200 bg-white/90 p-3">
            <ol className="space-y-2">
              {(Object.keys(STEP_COPY) as unknown as StepId[]).map((step) => {
                const active = currentStep === step;
                const unlocked = unlockedSteps[step];
                const complete = step < currentStep && unlocked;

                return (
                  <li key={step}>
                    <button
                      type="button"
                      disabled={!unlocked}
                      onClick={() => unlocked && setCurrentStep(step)}
                      className={`w-full rounded-xl border px-3 py-2 text-left transition ${
                        active
                          ? "border-teal-400 bg-teal-50"
                          : complete
                            ? "border-emerald-300 bg-emerald-50"
                            : unlocked
                              ? "border-slate-200 bg-white hover:bg-slate-50"
                              : "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400"
                      }`}
                    >
                      <p className="text-sm font-semibold text-slate-900">
                        {step}. {STEP_COPY[step].title.replace(/^\d+\.\s/, "")}
                      </p>
                      <p className="mt-1 text-xs text-slate-600">{STEP_COPY[step].subtitle}</p>
                    </button>
                  </li>
                );
              })}
            </ol>
          </nav>

          <BlurFade key={currentStep} className="rounded-2xl border border-slate-200 bg-white/95 p-5 shadow-sm md:p-6">
            <SectionTitle title={STEP_COPY[currentStep].title} subtitle={STEP_COPY[currentStep].subtitle} />

            {currentStep === 1 && (
              <section className="mt-4 space-y-4">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Scenario presets (demo)</p>
                  <div className="mt-2 grid gap-2 md:grid-cols-3">
                    {PRESETS.map((preset) => (
                      <button
                        key={preset.id}
                        type="button"
                        onClick={() => setSelectedPreset(preset.id)}
                        className={`rounded-lg border px-3 py-2 text-left text-sm transition ${
                          selectedPreset === preset.id
                            ? "border-teal-400 bg-teal-50"
                            : "border-slate-200 bg-white hover:bg-slate-50"
                        }`}
                      >
                        <p className="font-semibold text-slate-900">{preset.label}</p>
                        <p className="mt-1 text-xs text-slate-600">{preset.description}</p>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant={intakeMode === "manual" ? "default" : "outline"}
                    onClick={() => setIntakeMode("manual")}
                  >
                    Manual input
                  </Button>
                  <Button
                    type="button"
                    variant={intakeMode === "upload" ? "default" : "outline"}
                    onClick={() => setIntakeMode("upload")}
                  >
                    <Upload className="size-4" />
                    Upload PDF
                  </Button>
                </div>

                {intakeMode === "upload" && (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-sm font-medium text-slate-900">Upload proposal PDF and prefill fields</p>
                    <p className="mt-1 text-xs text-slate-600">If LLM extraction is unavailable, deterministic regex extraction is used automatically.</p>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <input
                        type="file"
                        accept="application/pdf"
                        onChange={(e) => setPdfFile(e.target.files?.[0] ?? null)}
                        className="field max-w-sm"
                      />
                      <Button type="button" onClick={onExtractFromPdf} disabled={extracting || !pdfFile}>
                        {extracting ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
                        {extracting ? "Extracting..." : "Extract details"}
                      </Button>
                    </div>
                    {extractionMeta && (
                      <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-700">
                        <p>
                          Mode: <strong>{extractionMeta.mode}</strong> | Confidence: <strong>{extractionMeta.confidence}</strong>
                        </p>
                        {extractionMeta.missing_fields.length > 0 && (
                          <p className="mt-1">Missing fields: {extractionMeta.missing_fields.join(", ")}</p>
                        )}
                        {extractionMeta.warnings.length > 0 && (
                          <ul className="mt-1 list-disc pl-5">
                            {extractionMeta.warnings.map((w) => (
                              <li key={w}>{w}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                    {extractError && <ErrorText text={extractError} />}
                  </div>
                )}

                <form onSubmit={onSubmitAssessment} className="space-y-4">
                  <Field label="Project address">
                    <input
                      className="field"
                      value={proposal.address}
                      onChange={(e) => setProposal((prev) => ({ ...prev, address: e.target.value }))}
                    />
                  </Field>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Province">
                      <select
                        className="field"
                        value={proposal.province}
                        onChange={(e) => setProposal((prev) => ({ ...prev, province: e.target.value as DataCentreProposal["province"] }))}
                      >
                        {PROVINCES.map((p) => (
                          <option key={p} value={p}>
                            {p}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="IT load (MW)">
                      <input
                        className="field"
                        type="number"
                        value={proposal.it_load_mw}
                        onChange={(e) => setProposal((prev) => ({ ...prev, it_load_mw: Number(e.target.value) }))}
                      />
                    </Field>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-3">
                    <Field label="PUE (power efficiency)">
                      <input
                        className="field"
                        type="number"
                        step="0.01"
                        value={proposal.pue}
                        onChange={(e) => setProposal((prev) => ({ ...prev, pue: Number(e.target.value) }))}
                      />
                    </Field>
                    <Field label="WUE (water efficiency)">
                      <input
                        className="field"
                        type="number"
                        step="0.01"
                        value={proposal.wue}
                        onChange={(e) => setProposal((prev) => ({ ...prev, wue: Number(e.target.value) }))}
                      />
                    </Field>
                    <Field label="CAPEX (CAD M)">
                      <input
                        className="field"
                        type="number"
                        value={proposal.capex_cad}
                        onChange={(e) => setProposal((prev) => ({ ...prev, capex_cad: Number(e.target.value) }))}
                      />
                    </Field>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Cooling type">
                      <select
                        className="field"
                        value={proposal.cooling_type}
                        onChange={(e) =>
                          setProposal((prev) => ({ ...prev, cooling_type: e.target.value as DataCentreProposal["cooling_type"] }))
                        }
                      >
                        <option value="air">air</option>
                        <option value="evaporative">evaporative</option>
                        <option value="liquid_immersion">liquid immersion</option>
                        <option value="hybrid">hybrid</option>
                      </select>
                    </Field>
                    <Field label="Facility type">
                      <select
                        className="field"
                        value={proposal.facility_type}
                        onChange={(e) =>
                          setProposal((prev) => ({ ...prev, facility_type: e.target.value as DataCentreProposal["facility_type"] }))
                        }
                      >
                        <option value="hyperscale">hyperscale</option>
                        <option value="enterprise">enterprise</option>
                        <option value="colocation">colocation</option>
                      </select>
                    </Field>
                  </div>

                  <div className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 sm:grid-cols-2">
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={proposal.has_onsite_generation}
                        onChange={(e) => setProposal((prev) => ({ ...prev, has_onsite_generation: e.target.checked }))}
                      />
                      On-site generation
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={proposal.renewable_ppa}
                        onChange={(e) => setProposal((prev) => ({ ...prev, renewable_ppa: e.target.checked }))}
                      />
                      Renewable PPA
                    </label>
                  </div>

                  <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-3 text-xs text-amber-900">
                    Inputs with highest sensitivity: <strong>IT load</strong>, <strong>PUE</strong>, and <strong>WUE</strong>. Small changes can move risk bands.
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    <p className="font-semibold text-slate-900">Expectation preview for this scenario</p>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
                      {PRESETS.find((p) => p.id === selectedPreset)?.expectedSignals.map((signal) => (
                        <li key={signal}>{signal}</li>
                      ))}
                    </ul>
                    {expectationSummary && (
                      <p className="mt-2 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700">{expectationSummary}</p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <ShinyButton
                      type="submit"
                      className="bg-teal-700 text-white disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={loading}
                    >
                      {loading ? "Running core assessment..." : "Run assessment"}
                    </ShinyButton>
                    {assessment && <span className="text-xs text-slate-600">Core assessment finished. Steps 2 and 3 are ready.</span>}
                  </div>
                </form>

                <ProgressPanel progress={progress} error={error} memoState={memoState} memoJobId={memoJobId} memoError={memoError} />
              </section>
            )}

            {currentStep === 2 && (
              <section className="mt-4">
                {!assessment ? (
                  <EmptyState text="Run the assessment first to open map context." />
                ) : (
                  <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_310px]">
                    <div className="space-y-3">
                      <div className="map-shell overflow-hidden rounded-2xl border border-slate-200 bg-slate-100">
                        <LocationContextMap
                          lat={assessment.location.lat}
                          lng={assessment.location.lng}
                          apiKey={MAPTILER_KEY}
                          noiseRadiusM={assessment.sociological.estimated_noise_radius_m}
                        />
                      </div>
                      <p className="text-sm text-slate-700">
                        {assessment.location.municipality}, {assessment.location.province} | lat {assessment.location.lat.toFixed(4)}, lng {assessment.location.lng.toFixed(4)}
                      </p>
                    </div>

                    <div className="space-y-3">
                      <GaugeCard
                        title="Water-share pressure"
                        value={`${assessment.environmental.pct_of_municipal_daily_supply.toFixed(2)}%`}
                        level={waterShareLevel(assessment.environmental.pct_of_municipal_daily_supply)}
                        widthPct={Math.min(100, assessment.environmental.pct_of_municipal_daily_supply * 8)}
                        description={waterShareMessage(assessment.environmental.pct_of_municipal_daily_supply)}
                      />
                      <GaugeCard
                        title="Grid strain signal"
                        value={toPct(assessment.grid_strain.strain_probability)}
                        level={gridLevel(assessment.grid_strain.strain_probability)}
                        widthPct={Math.min(100, assessment.grid_strain.strain_probability * 100)}
                        description={gridImplication(assessment.grid_strain)}
                      />
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Estimated acoustic radius</p>
                        <p className="mt-1 text-lg font-semibold text-slate-900">
                          {typeof assessment.sociological.estimated_noise_radius_m === "number"
                            ? `${assessment.sociological.estimated_noise_radius_m.toFixed(0)} m`
                            : "Unavailable"}
                        </p>
                        <p className="mt-1 text-xs text-slate-600">
                          This is a screening radius for where noise-management plans should be reviewed in detail.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {assessment && <TrustSummary dataFreshness={assessment.data_freshness} />}
              </section>
            )}

            {currentStep === 3 && (
              <section className="mt-4">
                {!assessment ? (
                  <EmptyState text="Run the assessment first to view impact results." />
                ) : (
                  <>
                    <div className="grid gap-3 md:grid-cols-3">
                      <ImpactCard
                        title="Environmental impact"
                        text={`Estimated annual emissions are ${assessment.environmental.annual_carbon_tonnes.toLocaleString()} tCO2e, and daily water demand is ${assessment.environmental.total_water_litres_per_day.toLocaleString()} L.`}
                      />
                      <ImpactCard
                        title="Economic impact"
                        text={`Estimated net fiscal impact over 10 years is $${assessment.economic.net_fiscal_impact_10yr_cad.toLocaleString()}, with ${assessment.economic.direct_permanent_jobs} direct permanent jobs.`}
                      />
                      <ImpactCard
                        title="Grid impact"
                        text={`Modelled grid strain probability is ${toPct(assessment.grid_strain.strain_probability)} (${assessment.grid_strain.predicted_strain_level}).`}
                      />
                    </div>

                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <MeaningCard
                        title="What this means for residents"
                        points={residentMeaning(assessment)}
                      />
                      <MeaningCard
                        title="What this means for council decisions"
                        points={councilMeaning(assessment)}
                      />
                    </div>

                    <details className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                      <summary className="cursor-pointer font-medium text-slate-900">Advanced details (methods and formulas)</summary>
                      <div className="mt-2 space-y-1 text-xs">
                        <p>Composite signal: {assessment.overall_score.summary_sentence}</p>
                        <p>Carbon formula: {evidenceText(assessment, "environmental", "carbon_formula")}</p>
                        <p>Water formula: {evidenceText(assessment, "environmental", "water_formula")}</p>
                        <p>Grid formula: {evidenceText(assessment, "environmental", "grid_formula")}</p>
                        <p>Jobs formula: {evidenceText(assessment, "economic", "jobs_formula")}</p>
                        <p>Fiscal formula: {evidenceText(assessment, "economic", "fiscal_formula")}</p>
                      </div>
                    </details>
                  </>
                )}
              </section>
            )}

            {currentStep === 4 && (
              <section className="mt-4">
                {!assessment ? (
                  <EmptyState text="Run the assessment first to open the decision brief." />
                ) : (
                  <>
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                      <p className="font-semibold text-slate-900">Shared recommendation</p>
                      <p className="mt-1">{plainLanguageSummary(assessment)}</p>
                    </div>

                    <div className="mt-3 rounded-xl border border-slate-200 bg-white p-3 text-sm">
                      <div className="flex items-center gap-2">
                        {memoState === "ready" ? (
                          <CheckCircle2 className="size-4 text-emerald-600" />
                        ) : memoState === "failed" ? (
                          <XCircle className="size-4 text-rose-600" />
                        ) : (
                          <Loader2 className="size-4 animate-spin text-slate-500" />
                        )}
                        <p className="font-medium text-slate-900">Memo generation status: {memoStateLabel(memoState)}</p>
                      </div>
                      {memoError && <p className="mt-1 text-xs text-rose-700">{memoError}</p>}
                      {memoState !== "ready" && (
                        <p className="mt-1 text-xs text-slate-600">You can continue reviewing this step while the narrative memo is generated in the background.</p>
                      )}
                    </div>

                    <div className="mt-4 flex gap-2">
                      <Button
                        type="button"
                        variant={persona === "citizen" ? "default" : "outline"}
                        onClick={() => setPersona("citizen")}
                      >
                        <UserRound className="size-4" />
                        Citizen
                      </Button>
                      <Button
                        type="button"
                        variant={persona === "councillor" ? "default" : "outline"}
                        onClick={() => setPersona("councillor")}
                      >
                        <Landmark className="size-4" />
                        Councillor
                      </Button>
                    </div>

                    <div className="mt-3 grid gap-3 md:grid-cols-3">
                      <ActionPhaseCard title="Now" items={phaseActions(assessment, persona).now} />
                      <ActionPhaseCard title="Before permit" items={phaseActions(assessment, persona).beforePermit} />
                      <ActionPhaseCard title="Post-approval monitoring" items={phaseActions(assessment, persona).postApproval} />
                    </div>

                    <details className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                      <summary className="cursor-pointer font-medium text-slate-900">Memo text and policy details</summary>
                      <div className="mt-2 space-y-2">
                        <p className="text-xs whitespace-pre-line text-slate-700">
                          {assessment.memo?.recommendation_section || assessment.report_narrative || "Memo is not available yet."}
                        </p>
                        {assessment.negotiation_playbook.length > 0 && (
                          <div className="rounded-lg border border-slate-200 bg-white p-2">
                            <p className="text-xs font-semibold text-slate-700">Negotiation playbook</p>
                            <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-slate-600">
                              {assessment.negotiation_playbook.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </details>
                  </>
                )}
              </section>
            )}
          </BlurFade>
        </div>

        <div className="mt-4 flex items-center justify-between rounded-2xl border border-slate-200 bg-white/90 p-3">
          <Button type="button" variant="outline" onClick={() => setCurrentStep((s) => Math.max(1, s - 1) as StepId)} disabled={currentStep === 1}>
            <ArrowLeft className="size-4" />
            Back
          </Button>
          <span className="text-xs font-medium text-slate-500">Step {currentStep} of 4</span>
          <Button
            type="button"
            onClick={() => setCurrentStep((s) => Math.min(4, s + 1) as StepId)}
            disabled={!canGoNext || currentStep === 4}
          >
            Next
            <ArrowRight className="size-4" />
          </Button>
        </div>
      </div>
    </main>
  );
}

function SectionTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <p className="text-xl font-semibold text-slate-900">{title}</p>
      <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm text-slate-700">
      <span className="mb-1 block font-medium">{label}</span>
      {children}
    </label>
  );
}

function ErrorText({ text }: { text: string }) {
  return <p className="mt-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">{text}</p>;
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-600">{text}</div>;
}

function ProgressPanel({
  progress,
  error,
  memoState,
  memoJobId,
  memoError,
}: {
  progress: StreamEvent | null;
  error: string | null;
  memoState: MemoState;
  memoJobId: string | null;
  memoError: string | null;
}) {
  if (!progress && !error && memoState === "idle") return null;

  return (
    <div className="space-y-3">
      {progress && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium text-slate-900">Progress: {progress.stage}</span>
            <span className="text-slate-600">{progress.pct}%</span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-teal-600 transition-all" style={{ width: `${progress.pct}%` }} />
          </div>
        </div>
      )}
      {memoState !== "idle" && (
        <div className="rounded-xl border border-slate-200 bg-white p-3 text-xs text-slate-700">
          <p>
            Memo job: <strong>{memoStateLabel(memoState)}</strong>
            {memoJobId ? ` (${memoJobId})` : ""}
          </p>
          {memoError && <p className="mt-1 text-rose-700">{memoError}</p>}
        </div>
      )}
      {error && <ErrorText text={error} />}
    </div>
  );
}

function ImpactCard({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      <p className="mt-1 text-sm text-slate-700">{text}</p>
    </div>
  );
}

function MeaningCard({ title, points }: { title: string; points: string[] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
        {points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
    </div>
  );
}

function GaugeCard({
  title,
  value,
  level,
  widthPct,
  description,
}: {
  title: string;
  value: string;
  level: "low" | "moderate" | "high";
  widthPct: number;
  description: string;
}) {
  const tone = level === "low" ? "bg-emerald-500" : level === "moderate" ? "bg-amber-500" : "bg-rose-500";

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <div className="mt-1 flex items-end justify-between">
        <p className="text-lg font-semibold text-slate-900">{value}</p>
        <span className="text-xs font-medium uppercase text-slate-600">{level}</span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full ${tone}`} style={{ width: `${Math.max(2, widthPct)}%` }} />
      </div>
      <p className="mt-2 text-xs text-slate-600">{description}</p>
    </div>
  );
}

function TrustSummary({ dataFreshness }: { dataFreshness: Record<string, string> }) {
  const trust = summarizeTrust(dataFreshness);

  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
      <div className="flex items-center gap-2">
        <ShieldCheck className="size-4 text-teal-700" />
        <p className="font-semibold text-slate-900">Trust summary ({trust.label} confidence)</p>
      </div>
      <p className="mt-1 text-xs text-slate-600">
        This assessment combines live feeds, official public datasets, and vetted reference data. We surface confidence at a high level so residents can focus on decisions, not internal source codes.
      </p>
      <p className="mt-2 text-xs text-slate-600">
        Live/cached signals: {trust.liveOrCached} | Reference datasets: {trust.reference} | Temporarily unavailable inputs: {trust.unavailable}
      </p>
    </div>
  );
}

function ActionPhaseCard({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function mergeExtractedProposal(current: DataCentreProposal, extracted: ExtractProposalResponse): DataCentreProposal {
  const next: DataCentreProposal = { ...current };

  if (typeof extracted.address === "string" && extracted.address.trim()) {
    next.address = extracted.address.trim();
  }

  if (typeof extracted.province === "string") {
    const province = extracted.province.toUpperCase() as DataCentreProposal["province"];
    if (PROVINCES.includes(province)) {
      next.province = province;
    }
  }

  const numericFields: Array<keyof Pick<DataCentreProposal, "it_load_mw" | "pue" | "wue" | "capex_cad" | "construction_months">> = [
    "it_load_mw",
    "pue",
    "wue",
    "capex_cad",
    "construction_months",
  ];

  for (const field of numericFields) {
    const value = extracted[field];
    if (typeof value === "number" && Number.isFinite(value)) {
      next[field] = value;
    }
  }

  if (extracted.cooling_type && ["air", "evaporative", "liquid_immersion", "hybrid"].includes(extracted.cooling_type)) {
    next.cooling_type = extracted.cooling_type;
  }

  if (extracted.facility_type && ["hyperscale", "enterprise", "colocation"].includes(extracted.facility_type)) {
    next.facility_type = extracted.facility_type;
  }

  if (typeof extracted.has_onsite_generation === "boolean") {
    next.has_onsite_generation = extracted.has_onsite_generation;
  }
  if (typeof extracted.renewable_ppa === "boolean") {
    next.renewable_ppa = extracted.renewable_ppa;
  }

  return next;
}

function summarizeTrust(dataFreshness: Record<string, string>) {
  const statuses = Object.values(dataFreshness).map((v) => String(v).toLowerCase());
  const liveOrCached = statuses.filter((v) => v.startsWith("live") || v.startsWith("cached")).length;
  const unavailable = statuses.filter((v) => v.startsWith("unavailable")).length;
  const reference = statuses.filter((v) => v.startsWith("static_reference")).length;

  const label = unavailable === 0 && liveOrCached >= 2 ? "high" : unavailable <= 2 ? "moderate" : "low";

  return { label, liveOrCached, unavailable, reference };
}

function evaluateScenarioMatch(scenarioId: ScenarioId, assessment: ImpactAssessment) {
  const rec = assessment.policy_decision?.recommendation ?? "";

  if (scenarioId === "beacon_high_load") {
    let matched = 0;
    if (assessment.environmental.pct_of_municipal_daily_supply >= 5) matched += 1;
    if (assessment.grid_strain.strain_probability >= 0.15) matched += 1;
    if (rec === "defer" || rec === "reject") matched += 1;
    return matched >= 2
      ? "Outcome check: matched expected stress-case direction (higher pressure signals)."
      : "Outcome check: partially matched stress-case expectation; review assumptions and location context.";
  }

  if (scenarioId === "balanced_qc") {
    const lowPressure = assessment.environmental.pct_of_municipal_daily_supply < 5 && assessment.grid_strain.strain_probability < 0.15;
    return lowPressure
      ? "Outcome check: matched expected lower-pressure direction for balanced QC profile."
      : "Outcome check: did not fully match expected lower-pressure direction; verify inputs.";
  }

  const baselineOkay = assessment.environmental.pct_of_municipal_daily_supply < 5 && assessment.grid_strain.strain_probability < 0.2;
  return baselineOkay
    ? "Outcome check: baseline behaved as expected for a moderate-load AB profile."
    : "Outcome check: baseline showed higher-than-expected pressure; inspect map context and assumptions.";
}

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
  return `Current recommendation: ${rec}. In plain terms, this project is ${a.overall_score.composite_rag} risk overall with the biggest sensitivity around water use, grid pressure, and operating efficiency assumptions.`;
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
    case "idle":
      return "not started";
    case "queued":
      return "queued";
    case "running":
      return "running";
    case "ready":
      return "ready";
    case "failed":
      return "failed";
    default:
      return state;
  }
}

function sleep(ms: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(() => resolve(), ms);
  });
}
