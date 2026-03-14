"use client";

import { useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, useMap } from "react-leaflet";

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

export function LocationContextMap({ lat, lng, apiKey }: { lat: number; lng: number; apiKey?: string }) {
  const MAPTILER_TILES = `https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${apiKey ?? ""}`;
  const OSM_TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
  const maptilerEnabled = process.env.NEXT_PUBLIC_USE_MAPTILER_TILES === "true" && Boolean(apiKey);
  const [useOsmFallback, setUseOsmFallback] = useState(!maptilerEnabled);
  const [tileErrorCount, setTileErrorCount] = useState(0);
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
      <MapContainer center={[lat, lng]} zoom={8} scrollWheelZoom={false} className="h-full w-full" style={{ height: "100%", width: "100%" }}>
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
        <CircleMarker center={[lat, lng]} radius={8} pathOptions={{ color: "#991b1b", fillColor: "#ef4444", fillOpacity: 0.95, weight: 2 }} />
        <EnsureSize />
        <Recenter lat={lat} lng={lng} />
      </MapContainer>
      {tileErrorCount > 3 && (
        <div className="pointer-events-none absolute inset-x-2 top-2 rounded-md border border-amber-300 bg-amber-50/95 px-2 py-1 text-xs text-amber-900">
          Tile provider errors detected. Showing OpenStreetMap fallback.
        </div>
      )}
    </div>
  );
}
