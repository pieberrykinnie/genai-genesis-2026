"use client";

import { useEffect, useMemo, useState } from "react";
import { Circle, CircleMarker, MapContainer, TileLayer, useMap } from "react-leaflet";

type SignalLevel = "low" | "moderate" | "high";

function waterSignal(pct?: number | null): SignalLevel | "n/a" {
  if (typeof pct !== "number" || !Number.isFinite(pct)) return "n/a";
  if (pct < 3) return "low";
  if (pct < 10) return "moderate";
  return "high";
}

function gridSignal(prob?: number | null): SignalLevel | "n/a" {
  if (typeof prob !== "number" || !Number.isFinite(prob)) return "n/a";
  if (prob < 0.1) return "low";
  if (prob < 0.25) return "moderate";
  return "high";
}

function signalClasses(level: SignalLevel | "n/a") {
  if (level === "low") return "border-emerald-300/70 bg-emerald-50/85 text-emerald-700";
  if (level === "moderate") return "border-amber-300/70 bg-amber-50/85 text-amber-700";
  if (level === "high") return "border-rose-300/70 bg-rose-50/85 text-rose-700";
  return "border-slate-200/70 bg-white/85 text-slate-600";
}

function Recenter({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();

  useEffect(() => {
    map.setView([lat, lng], map.getZoom(), { animate: false });
  }, [lat, lng, map]);

  return null;
}

function EnsureSize() {
  const map = useMap();

  useEffect(() => {
    const id = window.setTimeout(() => map.invalidateSize(), 0);
    return () => window.clearTimeout(id);
  }, [map]);

  return null;
}

export function LocationContextMap({
  lat,
  lng,
  apiKey,
  noiseRadiusM,
  waterSharePct,
  gridStrainProb,
  populationInNoiseZone,
  firstNationDistanceKm,
  municipality,
  province,
}: {
  lat: number;
  lng: number;
  apiKey?: string;
  noiseRadiusM?: number | null;
  waterSharePct?: number | null;
  gridStrainProb?: number | null;
  populationInNoiseZone?: number | null;
  firstNationDistanceKm?: number | null;
  municipality?: string;
  province?: string;
}) {
  const MAPTILER_TILES = `https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${apiKey ?? ""}`;
  const OSM_TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
  const maptilerEnabled = process.env.NEXT_PUBLIC_USE_MAPTILER_TILES === "true" && Boolean(apiKey);
  const [useOsmFallback, setUseOsmFallback] = useState(!maptilerEnabled);
  const [tileErrorCount, setTileErrorCount] = useState(0);
  const hasNoiseRadius = typeof noiseRadiusM === "number" && Number.isFinite(noiseRadiusM) && noiseRadiusM > 0;
  const scanRadiusM = hasNoiseRadius ? Math.max(noiseRadiusM * 1.6, 1200) : 1800;
  const waterLevel = waterSignal(waterSharePct);
  const gridLevel = gridSignal(gridStrainProb);
  const waterFillPct = typeof waterSharePct === "number" ? Math.min(100, Math.max(0, waterSharePct * 8)) : 0;
  const gridFillPct = typeof gridStrainProb === "number" ? Math.min(100, Math.max(0, gridStrainProb * 100)) : 0;
  const tileUrl = useOsmFallback ? OSM_TILES : MAPTILER_TILES;
  const attribution = useMemo(
    () =>
      useOsmFallback
        ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a>',
    [useOsmFallback],
  );

  return (
    <div className="relative h-full w-full">
      <div className="pointer-events-none absolute inset-0 z-[300] bg-gradient-to-br from-emerald-500/10 via-transparent to-cyan-500/10" />
      <MapContainer center={[lat, lng]} zoom={11} scrollWheelZoom={false} className="h-full w-full" style={{ height: "100%", width: "100%" }}>
        <TileLayer
          url={tileUrl}
          attribution={attribution}
          eventHandlers={{
            tileerror: () => {
              setTileErrorCount((n) => n + 1);
              setUseOsmFallback(true);
            },
          }}
        />
        <Circle
          center={[lat, lng]}
          radius={scanRadiusM}
          pathOptions={{ color: "#06b6d4", fillColor: "#22d3ee", fillOpacity: 0.06, weight: 2, dashArray: "6 10", className: "map-scan-ring" }}
        />
        <CircleMarker center={[lat, lng]} radius={8} pathOptions={{ color: "#991b1b", fillColor: "#ef4444", fillOpacity: 0.95, weight: 2 }} />
        {hasNoiseRadius && (
          <Circle
            center={[lat, lng]}
            radius={noiseRadiusM}
            pathOptions={{ color: "#b45309", fillColor: "#f59e0b", fillOpacity: 0.14, weight: 2 }}
          />
        )}
        <EnsureSize />
        <Recenter lat={lat} lng={lng} />
      </MapContainer>
      <div className="pointer-events-none absolute left-2 top-2 z-[450] rounded-md border border-emerald-200/70 bg-white/90 px-3 py-2 shadow-sm backdrop-blur">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Location Context Analysis</p>
        <p className="mt-0.5 text-xs font-medium text-slate-700">{municipality ?? "Site"}{province ? `, ${province}` : ""}</p>
        <p className="text-[11px] text-slate-500">
          {lat.toFixed(3)}°N, {lng.toFixed(3)}°W
        </p>
      </div>

      <div className="pointer-events-none absolute bottom-2 right-2 z-[450] w-[245px] rounded-md border border-slate-200/80 bg-white/92 px-3 py-2.5 shadow-sm backdrop-blur">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Signals</p>

        <div className="mt-1.5">
          <div className="mb-1 flex items-center justify-between text-[11px]">
            <span className="font-semibold text-slate-600">Water-share pressure</span>
            <span className={`rounded-full border px-2 py-0.5 font-semibold ${signalClasses(waterLevel)}`}>
              {typeof waterSharePct === "number" ? `${waterSharePct.toFixed(2)}%` : "n/a"}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-200/80">
            <div className="map-meter-fill h-full bg-amber-500" style={{ width: `${waterFillPct}%` }} />
          </div>
        </div>

        <div className="mt-2">
          <div className="mb-1 flex items-center justify-between text-[11px]">
            <span className="font-semibold text-slate-600">Grid strain</span>
            <span className={`rounded-full border px-2 py-0.5 font-semibold ${signalClasses(gridLevel)}`}>
              {typeof gridStrainProb === "number" ? `${(gridStrainProb * 100).toFixed(1)}%` : "n/a"}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-200/80">
            <div className="map-meter-fill h-full bg-emerald-500" style={{ width: `${gridFillPct}%` }} />
          </div>
        </div>

        <p className="mt-2 text-[10px] text-slate-500">
          Noise zone pop: {typeof populationInNoiseZone === "number" ? populationInNoiseZone.toLocaleString() : "n/a"}
          {" · "}
          Nearest FN: {typeof firstNationDistanceKm === "number" ? `${firstNationDistanceKm.toFixed(1)} km` : "n/a"}
        </p>
      </div>

      <div className="pointer-events-none absolute bottom-2 left-2 max-w-[260px] rounded-md border border-slate-200 bg-white/95 px-2 py-1 text-[11px] text-slate-700 shadow-sm">
        <p className="font-semibold text-slate-800">Map Legend</p>
        <p>
          <span className="inline-block h-2 w-2 rounded-full bg-red-500 align-middle" /> Site marker
        </p>
        <p>
          <span className="inline-block h-2 w-2 rounded-full border border-cyan-600 bg-cyan-200/60 align-middle" /> Context scan radius: {scanRadiusM.toFixed(0)} m
        </p>
        <p>
          <span className="inline-block h-2 w-2 rounded-full border border-amber-700 bg-amber-200/60 align-middle" /> Estimated acoustic influence radius:{" "}
          {hasNoiseRadius ? `${noiseRadiusM?.toFixed(0)} m` : "unavailable"}
        </p>
        <p className="text-slate-500">Source: deterministic model</p>
      </div>
      {tileErrorCount > 3 && (
        <div className="pointer-events-none absolute inset-x-2 top-2 rounded-md border border-amber-300 bg-amber-50/95 px-2 py-1 text-xs text-amber-900">
          Tile provider errors detected. Showing OpenStreetMap fallback.
        </div>
      )}
    </div>
  );
}
