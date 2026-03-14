"use client";

import { FormEvent, useMemo, useState } from "react";

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

export default function Home() {
  const [proposal, setProposal] = useState<DataCentreProposal>(DEFAULT_PROPOSAL);
  const [assessment, setAssessment] = useState<ImpactAssessment | null>(null);
  const [progress, setProgress] = useState<StreamEvent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scoreTone = useMemo(() => {
    const score = assessment?.overall_score.composite_rag ?? "amber";
    if (score === "green") return "text-emerald-700 bg-emerald-100";
    if (score === "red") return "text-rose-700 bg-rose-100";
    return "text-amber-700 bg-amber-100";
  }, [assessment?.overall_score.composite_rag]);

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
    <div className="min-h-screen px-4 py-10 sm:px-8 lg:px-12">
      <div className="mx-auto grid w-full max-w-7xl gap-8 lg:grid-cols-[1.1fr_1fr]">
        <section className="rounded-2xl border border-black/10 bg-white/85 p-6 shadow-lg backdrop-blur sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">GenAI Genesis 2026</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            DataSite Impact Analyzer
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            Evaluate data centre proposals using Canadian grid, community, and environmental context with deterministic scoring + ML strain prediction.
          </p>

          <form onSubmit={onSubmit} className="mt-8 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700">Address</label>
              <input
                className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none ring-emerald-400 focus:ring"
                value={proposal.address}
                onChange={(e) => setProposal((p) => ({ ...p, address: e.target.value }))}
              />
            </div>

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
                  step="0.01"
                  className="field"
                  value={proposal.pue}
                  onChange={(e) => setProposal((p) => ({ ...p, pue: Number(e.target.value) }))}
                />
              </Field>
              <Field label="WUE">
                <input
                  type="number"
                  step="0.01"
                  className="field"
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
              <Field label="Cooling">
                <select
                  className="field"
                  value={proposal.cooling_type}
                  onChange={(e) => setProposal((p) => ({ ...p, cooling_type: e.target.value as DataCentreProposal["cooling_type"] }))}
                >
                  <option value="air">air</option>
                  <option value="evaporative">evaporative</option>
                  <option value="liquid_immersion">liquid_immersion</option>
                  <option value="hybrid">hybrid</option>
                </select>
              </Field>
              <Field label="Facility">
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

            <button
              type="submit"
              disabled={loading}
              className="inline-flex rounded-xl bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white shadow hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-emerald-400"
            >
              {loading ? "Assessing..." : "Run Assessment"}
            </button>
          </form>

          {progress && (
            <div className="mt-6 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-900">
              <p className="font-medium">Progress: {progress.stage}</p>
              <p>{progress.pct}%</p>
            </div>
          )}

          {error && <div className="mt-4 rounded-xl bg-rose-50 p-4 text-sm text-rose-700">{error}</div>}
        </section>

        <section className="rounded-2xl border border-black/10 bg-white/90 p-6 shadow-lg sm:p-8">
          <h2 className="text-xl font-semibold text-slate-900">Assessment</h2>
          {!assessment && <p className="mt-3 text-sm text-slate-600">Run a proposal to view environmental, economic, and sociological outputs.</p>}

          {assessment && (
            <div className="mt-4 space-y-4 text-sm text-slate-700">
              <div className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase ${scoreTone}`}>
                Composite: {assessment.overall_score.composite_rag}
              </div>
              <p>{assessment.overall_score.summary_sentence}</p>

              <Card title="Environmental">
                <Line label="Annual Carbon" value={`${assessment.environmental.annual_carbon_tonnes.toLocaleString()} tCO2e`} />
                <Line label="Water / day" value={`${assessment.environmental.total_water_litres_per_day.toLocaleString()} L`} />
                <Line label="Water Share" value={`${assessment.environmental.pct_of_municipal_daily_supply.toFixed(2)}%`} />
                <Line label="Grid Strain Score" value={assessment.environmental.grid_score} />
              </Card>

              <Card title="Economic">
                <Line label="Permanent Jobs" value={`${assessment.economic.direct_permanent_jobs}`} />
                <Line label="10y Tax Revenue" value={`$${assessment.economic.estimated_total_tax_revenue_10yr_cad.toLocaleString()}`} />
                <Line label="Net Fiscal 10y" value={`$${assessment.economic.net_fiscal_impact_10yr_cad.toLocaleString()}`} />
              </Card>

              <Card title="ML Grid Prediction">
                <Line label="Strain Probability" value={`${(assessment.grid_strain.strain_probability * 100).toFixed(1)}%`} />
                <Line label="Rate Increase Probability" value={`${(assessment.grid_strain.rate_increase_probability * 100).toFixed(1)}%`} />
                <Line label="Predicted Level" value={assessment.grid_strain.predicted_strain_level} />
                <Line label="Model Version" value={assessment.grid_strain.model_version} />
              </Card>
            </div>
          )}
        </section>
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

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      <div className="mt-2 space-y-1">{children}</div>
    </div>
  );
}

function Line({ label, value }: { label: string; value: string }) {
  return (
    <p className="flex items-center justify-between gap-4">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-900">{value}</span>
    </p>
  );
}
