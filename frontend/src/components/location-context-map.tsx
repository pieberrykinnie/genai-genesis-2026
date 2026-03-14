"use client";

import { useEffect } from "react";
import { CircleMarker, MapContainer, TileLayer, useMap } from "react-leaflet";

function Recenter({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();

  useEffect(() => {
    map.setView([lat, lng], map.getZoom(), { animate: false });
  }, [lat, lng, map]);

  return null;
}

export function LocationContextMap({ lat, lng, apiKey }: { lat: number; lng: number; apiKey: string }) {
  const tileUrl = `https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${apiKey}`;

  return (
    <MapContainer center={[lat, lng]} zoom={8} scrollWheelZoom={false} className="h-full w-full">
      <TileLayer
        url={tileUrl}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a>'
      />
      <CircleMarker center={[lat, lng]} radius={8} pathOptions={{ color: "#991b1b", fillColor: "#ef4444", fillOpacity: 0.95, weight: 2 }} />
      <Recenter lat={lat} lng={lng} />
    </MapContainer>
  );
}
