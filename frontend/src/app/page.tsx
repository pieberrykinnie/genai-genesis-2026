"use client";

import { FormEvent, useMemo, useState } from "react";
import dynamic from "next/dynamic";

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

  const activeStep = useMemo(() => {
    if (!progress && !assessment) return 1;
    if (progress && progress.pct < 35) return 1;
    if ((progress && progress.pct < 55) || (!progress && assessment)) return 2;
    if (progress && progress.pct < 85) return 3;
    if (assessment) return 4;
    return 1;
  }, [assessment, progress]);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setAssessment(null);
    setProgress({ stage: "starting", pct: 0 });

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
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="hero-panel rounded-3xl p-6 md:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-900/80">City Decision Support</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">DataSite Impact Analyzer</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">
            Understand what a data centre proposal means for local power, water, tax impact, and community risk before approval.
          </p>
        </header>

        <Stepper activeStep={activeStep} />

        <section className="grid gap-6 lg:grid-cols-[1.05fr_1fr]">
          <Card title="1. Proposal Intake" subtitle="Enter project details used by the impact model.">
            <form onSubmit={onSubmit} className="space-y-4">
              <Field label="Project Address">
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
                <Field label="IT Load (MW)">
                  <input
                    type="number"
                    className="field"
                    value={proposal.it_load_mw}
                    onChange={(e) => setProposal((p) => ({ ...p, it_load_mw: Number(e.target.value) }))}
                  />
                </Field>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <Field label="PUE">
                  <input
                    type="number"
                    className="field"
                    step="0.01"
                    value={proposal.pue}
                    onChange={(e) => setProposal((p) => ({ ...p, pue: Number(e.target.value) }))}
                  />
                </Field>
                <Field label="WUE">
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
                <Field label="Cooling Type">
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
                <Field label="Facility Type">
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

              <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900">
                Inputs with highest sensitivity: <strong>IT load</strong>, <strong>PUE</strong>, and <strong>WUE</strong>. Small changes can move risk bands.
              </div>

              <button
                type="submit"
                disabled={loading}
                className="inline-flex rounded-xl bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white shadow hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-emerald-400"
              >
                {loading ? "Running Assessment..." : "Run Assessment"}
              </button>
            </form>

            {progress && (
              <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-900">Progress: {progress.stage}</span>
                  <span className="text-slate-600">{progress.pct}%</span>
                </div>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
                  <div className="h-full rounded-full bg-emerald-600 transition-all" style={{ width: `${progress.pct}%` }} />
                </div>
              </div>
            )}

            {error && <p className="mt-3 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
          </Card>

          <Card title="2. Location Context" subtitle="Map and immediate risk context for this site.">
            <LocationMap assessment={assessment} />
            {!assessment && <p className="mt-3 text-sm text-slate-500">Run assessment to populate map context.</p>}
            {assessment && (
              <div className="mt-4 flex flex-wrap gap-2">
                <RiskChip label="Grid" value={assessment.environmental.grid_score} />
                <RiskChip label="Water Share" value={`${assessment.environmental.pct_of_municipal_daily_supply.toFixed(2)}%`} />
                <RiskChip label="AQHI" value={assessment.sociological.air_quality_baseline} />
                <RiskChip
                  label="Noise Radius"
                  value={
                    typeof assessment.sociological.estimated_noise_radius_m === "number"
                      ? `${assessment.sociological.estimated_noise_radius_m.toFixed(0)} m`
                      : "unavailable"
                  }
                />
              </div>
            )}
          </Card>
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <Card title="3. Impact Results" subtitle="Plain-language summary for council discussion.">
            {!assessment && <p className="text-sm text-slate-500">Results appear after the model run completes.</p>}
            {assessment && (
              <div className="space-y-4 text-sm">
                <NarrativeBlock
                  title="Environmental"
                  sentence={`Annual emissions are about ${assessment.environmental.annual_carbon_tonnes.toLocaleString()} tCO2e and daily water demand is ${assessment.environmental.total_water_litres_per_day.toLocaleString()} L.`}
                />
                <NarrativeBlock
                  title="Economic"
                  sentence={`Estimated net fiscal impact over 10 years is $${assessment.economic.net_fiscal_impact_10yr_cad.toLocaleString()} with ${assessment.economic.direct_permanent_jobs} direct permanent jobs.`}
                />
                <NarrativeBlock
                  title="Grid"
                  sentence={`Model predicts ${toPct(assessment.grid_strain.strain_probability)} grid strain probability (${assessment.grid_strain.predicted_strain_level}).`}
                />
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-slate-700">
                  <p className="font-semibold text-slate-900">Composite Decision Signal</p>
                  <p className="mt-1">{assessment.overall_score.summary_sentence}</p>
                </div>
              </div>
            )}
          </Card>

          <Card title="4. Decision Brief" subtitle="Negotiation actions and evidence trail.">
            {!assessment && <p className="text-sm text-slate-500">Decision brief appears after results are generated.</p>}
            {assessment && (
              <div className="space-y-4 text-sm">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Negotiation Playbook</p>
                  <ol className="mt-2 list-decimal space-y-1 pl-5">
                    {assessment.negotiation_playbook.map((item) => (
                      <li key={item} className="text-slate-700">
                        {item}
                      </li>
                    ))}
                  </ol>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Data Freshness / Evidence</p>
                  <div className="mt-2 max-h-44 overflow-auto rounded-xl border border-slate-200">
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
                </div>
              </div>
            )}
          </Card>
        </section>
      </div>
    </main>
  );
}

function toPct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function Stepper({ activeStep }: { activeStep: number }) {
  const steps = ["Proposal Intake", "Location Context", "Impact Results", "Decision Brief"];
  return (
    <div className="grid gap-2 rounded-2xl border border-slate-200 bg-white/80 p-3 sm:grid-cols-4">
      {steps.map((label, idx) => {
        const num = idx + 1;
        const active = num === activeStep;
        const complete = num < activeStep;
        return (
          <div
            key={label}
            className={`rounded-xl px-3 py-2 text-xs font-medium ${
              active ? "bg-emerald-700 text-white" : complete ? "bg-emerald-100 text-emerald-900" : "bg-slate-100 text-slate-500"
            }`}
          >
            {num}. {label}
          </div>
        );
      })}
    </div>
  );
}

function LocationMap({ assessment }: { assessment: ImpactAssessment | null }) {
  if (!assessment) {
    return <div className="map-shell flex items-center justify-center text-sm text-slate-500">Map preview appears after assessment.</div>;
  }

  const { lng, lat } = assessment.location;
  const noiseRadiusM = assessment.sociological.estimated_noise_radius_m;

  return (
    <div className="map-shell overflow-hidden rounded-2xl border border-slate-200 bg-slate-100">
      <LocationContextMap lat={lat} lng={lng} apiKey={MAPTILER_KEY} noiseRadiusM={noiseRadiusM} />
      <div className="border-t border-slate-200 bg-white/90 px-3 py-2 text-xs text-slate-700">
        {assessment.location.municipality}, {assessment.location.province} | lat {lat.toFixed(4)}, lng {lng.toFixed(4)}
      </div>
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

function Card({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm md:p-6">
      <p className="text-lg font-semibold text-slate-900">{title}</p>
      <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
      <div className="mt-4">{children}</div>
    </section>
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

function NarrativeBlock({ title, sentence }: { title: string; sentence: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <p className="font-semibold text-slate-900">{title}</p>
      <p className="mt-1 text-slate-700">{sentence}</p>
    </div>
  );
}
