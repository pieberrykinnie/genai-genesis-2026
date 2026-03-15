"use client";

import { FormEvent, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { ArrowLeft, ArrowRight, Landmark, UserRound } from "lucide-react";

import { AnimatedGradientText } from "@/components/magicui/animated-gradient-text";
import { BlurFade } from "@/components/magicui/blur-fade";
import { ShinyButton } from "@/components/magicui/shiny-button";
import { Button } from "@/components/ui/button";
import type { DataCentreProposal, ImpactAssessment, StreamEvent } from "@/types/assessment";

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

const STEPS = ["Proposal", "Location", "Impacts", "Decision"] as const;
type Persona = "citizen" | "councillor";

const MAPTILER_KEY = process.env.NEXT_PUBLIC_MAPTILER_API_KEY;
const LocationContextMap = dynamic(() => import("@/components/location-context-map").then((mod) => mod.LocationContextMap), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading map...</div>,
});

export default function Home() {
  const [proposal, setProposal] = useState<DataCentreProposal>(DEFAULT_PROPOSAL);
  const [assessment, setAssessment] = useState<ImpactAssessment | null>(null);
  const [progress, setProgress] = useState<StreamEvent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [persona, setPersona] = useState<Persona>("citizen");

  const canGoNext = useMemo(() => {
    if (currentStep === 1) return Boolean(assessment);
    return currentStep < 4;
  }, [assessment, currentStep]);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setAssessment(null);
    setProgress({ stage: "starting", pct: 0 });
    setCurrentStep(1);

    try {
      const res = await fetch("/api/assess/stream", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(proposal),
      });

      if (!res.ok || !res.body) {
        const message = await res.text();
        throw new Error(message || "stream request failed");
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
          const payload = line.slice(5).trim();
          if (!payload) continue;

          const evt = JSON.parse(payload) as StreamEvent;
          setProgress(evt);
          if (evt.stage === "error") {
            throw new Error(typeof evt.error === "string" ? evt.error : JSON.stringify(evt.error));
          }
          if (evt.stage === "complete" && evt.result) {
            setAssessment(evt.result);
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen px-4 py-8 md:px-8 md:py-10">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
        <header className="hero-panel rounded-3xl px-6 py-7 md:px-8 md:py-9">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-900/80">Council + Public Decision Tool</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
            DataSite <AnimatedGradientText speed={1.6}>Impact Analyzer</AnimatedGradientText>
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">
            Understand what a proposed data centre could mean for your grid, water, taxes, and local quality of life.
          </p>
        </header>

        <StepHeader currentStep={currentStep} onStepClick={setCurrentStep} />

        <BlurFade key={currentStep} className="rounded-2xl border border-slate-200 bg-white/95 p-5 shadow-sm md:p-6">
          {currentStep === 1 && (
            <section>
              <SectionTitle title="1. Proposal" subtitle="Enter the project details you want assessed." />
              <form onSubmit={onSubmit} className="mt-4 space-y-4">
                <Field label="Project address">
                  <input
                    className="field"
                    value={proposal.address}
                    onChange={(e) => setProposal((p) => ({ ...p, address: e.target.value }))}
                    placeholder="e.g., Grande Prairie, Alberta"
                  />
                </Field>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Province">
                    <select
                      className="field"
                      value={proposal.province}
                      onChange={(e) => setProposal((p) => ({ ...p, province: e.target.value as DataCentreProposal["province"] }))}
                    >
                      {["ON", "AB", "BC", "QC", "MB", "SK", "NS", "NB", "NL", "PE"].map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="IT load (MW)">
                    <input
                      type="number"
                      className="field"
                      value={proposal.it_load_mw}
                      onChange={(e) => setProposal((p) => ({ ...p, it_load_mw: Number(e.target.value) }))}
                    />
                  </Field>
                </div>

                <div className="grid gap-4 sm:grid-cols-3">
                  <Field label="PUE (power efficiency)">
                    <input
                      type="number"
                      className="field"
                      step="0.01"
                      value={proposal.pue}
                      onChange={(e) => setProposal((p) => ({ ...p, pue: Number(e.target.value) }))}
                    />
                  </Field>
                  <Field label="WUE (water efficiency)">
                    <input
                      type="number"
                      className="field"
                      step="0.01"
                      value={proposal.wue}
                      onChange={(e) => setProposal((p) => ({ ...p, wue: Number(e.target.value) }))}
                    />
                  </Field>
                  <Field label="CAPEX (CAD M)">
                    <input
                      type="number"
                      className="field"
                      value={proposal.capex_cad}
                      onChange={(e) => setProposal((p) => ({ ...p, capex_cad: Number(e.target.value) }))}
                    />
                  </Field>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Cooling type">
                    <select
                      className="field"
                      value={proposal.cooling_type}
                      onChange={(e) => setProposal((p) => ({ ...p, cooling_type: e.target.value as DataCentreProposal["cooling_type"] }))}
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
                      onChange={(e) => setProposal((p) => ({ ...p, facility_type: e.target.value as DataCentreProposal["facility_type"] }))}
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
                      onChange={(e) => setProposal((p) => ({ ...p, has_onsite_generation: e.target.checked }))}
                    />
                    On-site power generation
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      checked={proposal.renewable_ppa}
                      onChange={(e) => setProposal((p) => ({ ...p, renewable_ppa: e.target.checked }))}
                    />
                    Renewable power contract (PPA)
                  </label>
                </div>

                <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-3 text-xs text-amber-900">
                  Most sensitive inputs: <strong>IT load</strong>, <strong>PUE</strong>, and <strong>WUE</strong>.
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <ShinyButton type="submit" className="bg-emerald-600 text-white disabled:cursor-not-allowed disabled:opacity-60" disabled={loading}>
                    {loading ? "Running assessment..." : "Run assessment"}
                  </ShinyButton>
                  {assessment && <span className="text-xs text-slate-500">Assessment ready. Move to the next step.</span>}
                </div>
              </form>

              <ProgressPanel progress={progress} error={error} />
            </section>
          )}

          {currentStep === 2 && (
            <section>
              <SectionTitle title="2. Location" subtitle="See where the site sits and nearby risk context." />
              {!assessment ? (
                <EmptyState text="Run the assessment first, then return here to review the map." />
              ) : (
                <>
                  <div className="map-shell mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-slate-100">
                    <LocationContextMap
                      lat={assessment.location.lat}
                      lng={assessment.location.lng}
                      apiKey={MAPTILER_KEY}
                      noiseRadiusM={assessment.sociological.estimated_noise_radius_m}
                    />
                  </div>
                  <p className="mt-3 text-sm text-slate-700">
                    {assessment.location.municipality}, {assessment.location.province} | lat {assessment.location.lat.toFixed(4)}, lng {assessment.location.lng.toFixed(4)}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <RiskChip label="Grid status" value={assessment.environmental.grid_score} />
                    <RiskChip label="Water share" value={`${assessment.environmental.pct_of_municipal_daily_supply.toFixed(2)}%`} />
                    <RiskChip label="AQHI" value={assessment.sociological.air_quality_baseline} />
                    <RiskChip
                      label="Noise radius"
                      value={
                        typeof assessment.sociological.estimated_noise_radius_m === "number"
                          ? `${assessment.sociological.estimated_noise_radius_m.toFixed(0)} m`
                          : "unavailable"
                      }
                    />
                  </div>
                  <details className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    <summary className="cursor-pointer font-medium text-slate-900">Details and source status</summary>
                    <p className="mt-2 text-xs text-slate-500">Data freshness is shown exactly as returned by each source.</p>
                    <div className="mt-2 max-h-56 overflow-auto rounded-lg border border-slate-200 bg-white">
                      <table className="w-full border-collapse text-left text-xs">
                        <thead className="bg-slate-50 text-slate-500">
                          <tr>
                            <th className="px-3 py-2">Source</th>
                            <th className="px-3 py-2">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(assessment.data_freshness).map(([k, v]) => (
                            <tr key={k} className="border-t border-slate-100">
                              <td className="px-3 py-2 font-medium text-slate-700">{k}</td>
                              <td className="px-3 py-2 text-slate-600">{String(v)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                </>
              )}
            </section>
          )}

          {currentStep === 3 && (
            <section>
              <SectionTitle title="3. Impacts" subtitle="Plain-language impact summary for this proposal." />
              {!assessment ? (
                <EmptyState text="Run the assessment first to view impact results." />
              ) : (
                <>
                  <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <ImpactCard
                      title="Environmental"
                      text={`Estimated annual emissions are ${assessment.environmental.annual_carbon_tonnes.toLocaleString()} tCO2e, with ${assessment.environmental.total_water_litres_per_day.toLocaleString()} L/day water demand.`}
                    />
                    <ImpactCard
                      title="Economic"
                      text={`Estimated 10-year net fiscal effect is $${assessment.economic.net_fiscal_impact_10yr_cad.toLocaleString()} and ${assessment.economic.direct_permanent_jobs} direct permanent jobs.`}
                    />
                    <ImpactCard
                      title="Grid"
                      text={`Grid model predicts ${toPct(assessment.grid_strain.strain_probability)} strain probability (${assessment.grid_strain.predicted_strain_level}).`}
                    />
                  </div>

                  <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    <p className="font-semibold text-slate-900">Composite signal</p>
                    <p className="mt-1">{assessment.overall_score.summary_sentence}</p>
                  </div>

                  <details className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    <summary className="cursor-pointer font-medium text-slate-900">How these numbers were calculated</summary>
                    <div className="mt-2 space-y-1 text-xs">
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
            <section>
              <SectionTitle title="4. Decision" subtitle="Action guidance for both residents and councillors." />
              {!assessment ? (
                <EmptyState text="Run the assessment first to generate recommendations." />
              ) : (
                <>
                  <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    <p className="font-semibold text-slate-900">Shared outcome</p>
                    <p className="mt-1">{assessment.overall_score.summary_sentence}</p>
                    <p className="mt-1">Recommendation: <strong>{assessment.policy_decision?.recommendation?.replaceAll("_", " ") ?? "not available"}</strong></p>
                  </div>

                  <div className="mt-4 flex gap-2">
                    <Button
                      type="button"
                      variant={persona === "citizen" ? "default" : "outline"}
                      onClick={() => setPersona("citizen")}
                      className="h-9"
                    >
                      <UserRound className="size-4" />
                      Citizen
                    </Button>
                    <Button
                      type="button"
                      variant={persona === "councillor" ? "default" : "outline"}
                      onClick={() => setPersona("councillor")}
                      className="h-9"
                    >
                      <Landmark className="size-4" />
                      Councillor
                    </Button>
                  </div>

                  <div className="mt-3 rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-900">
                      {persona === "citizen" ? "If you are a citizen, here is what you can do:" : "If you are a councillor, here is what you can do:"}
                    </p>
                    <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm text-slate-700">
                      {(persona === "citizen" ? citizenActions(assessment) : councillorActions(assessment)).map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ol>
                  </div>

                  <details className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    <summary className="cursor-pointer font-medium text-slate-900">Memo and evidence details</summary>
                    <div className="mt-2 space-y-2">
                      <p className="text-xs text-slate-600 whitespace-pre-line">{assessment.memo?.recommendation_section ?? assessment.report_narrative}</p>
                      <div className="rounded-lg border border-slate-200 bg-white p-2">
                        <p className="text-xs font-semibold text-slate-700">Negotiation playbook</p>
                        <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-slate-600">
                          {assessment.negotiation_playbook.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </details>
                </>
              )}
            </section>
          )}
        </BlurFade>

        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white/90 p-3">
          <Button type="button" variant="outline" onClick={() => setCurrentStep((s) => Math.max(1, s - 1))} disabled={currentStep === 1}>
            <ArrowLeft className="size-4" />
            Back
          </Button>
          <span className="text-xs font-medium text-slate-500">Step {currentStep} of 4</span>
          <Button
            type="button"
            onClick={() => setCurrentStep((s) => Math.min(4, s + 1))}
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
      <p className="text-lg font-semibold text-slate-900">{title}</p>
      <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
    </div>
  );
}

function StepHeader({ currentStep, onStepClick }: { currentStep: number; onStepClick: (step: number) => void }) {
  return (
    <div className="grid gap-2 rounded-2xl border border-slate-200 bg-white/85 p-2 sm:grid-cols-4">
      {STEPS.map((label, idx) => {
        const step = idx + 1;
        const stateClass =
          step === currentStep
            ? "bg-emerald-700 text-white"
            : step < currentStep
              ? "bg-emerald-100 text-emerald-900"
              : "bg-slate-100 text-slate-500";
        return (
          <button
            type="button"
            key={label}
            className={`rounded-xl px-3 py-2 text-left text-xs font-semibold transition ${stateClass}`}
            onClick={() => onStepClick(step)}
          >
            {step}. {label}
          </button>
        );
      })}
    </div>
  );
}

function ProgressPanel({ progress, error }: { progress: StreamEvent | null; error: string | null }) {
  if (!progress && !error) return null;

  return (
    <div className="mt-4 space-y-3">
      {progress && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium text-slate-900">Progress: {progress.stage}</span>
            <span className="text-slate-600">{progress.pct}%</span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-emerald-600 transition-all" style={{ width: `${progress.pct}%` }} />
          </div>
        </div>
      )}
      {error && <p className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
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

function RiskChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
      <span className="text-slate-500">{label}</span>
      <span>{value}</span>
    </span>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-600">
      {text}
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

function toPct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
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

function citizenActions(assessment: ImpactAssessment): string[] {
  const actions: string[] = [];
  const rec = assessment.policy_decision?.recommendation ?? "";

  if (assessment.environmental.water_score === "red" || assessment.environmental.pct_of_municipal_daily_supply >= 10) {
    actions.push("Ask for a public monthly water-use report and a clear water replenishment plan.");
  }
  if (assessment.grid_strain.strain_probability >= 0.25) {
    actions.push("Ask how household power rates could change and what protections are planned.");
  } else {
    actions.push("Ask council to publish yearly grid and utility-rate impact updates.");
  }
  if (rec === "defer" || rec === "reject") {
    actions.push("Support a pause until independent technical review results are published.");
  } else {
    actions.push("Request public progress checkpoints tied to water, jobs, and noise commitments.");
  }

  return actions;
}

function councillorActions(assessment: ImpactAssessment): string[] {
  const actions: string[] = [];

  for (const item of assessment.negotiation_playbook.slice(0, 3)) {
    actions.push(item);
  }

  if (assessment.environmental.water_score === "red") {
    actions.push("Make incentives conditional on audited water caps and enforceable clawbacks.");
  }

  const unavailableSources = Object.values(assessment.data_freshness).filter((v) => String(v).startsWith("unavailable:")).length;
  if (unavailableSources > 0) {
    actions.push("Record data gaps in the motion and require refreshed evidence before final approval.");
  }

  return actions.slice(0, 4);
}
