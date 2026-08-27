"use client";

import { Alert, Box, Button, Dialog, DialogActions, DialogContent, Stack, Typography } from "@mui/material";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/feedback/EmptyState";
import type { MarketBrief } from "@/types/domain";

type Approach = "overlap" | "investigate" | "serving";

type HeatCity = {
  id: string;
  name: string;
  score: number | null;
  approach: Approach;
  x: number;
  y: number;
};

const CITY_POINTS: Record<string, { lat: number; lng: number }> = {
  karachi: { lat: 24.86, lng: 67.0 },
  hyderabad: { lat: 25.4, lng: 68.37 },
  lahore: { lat: 31.52, lng: 74.36 },
  faisalabad: { lat: 31.42, lng: 73.08 },
  rawalpindi: { lat: 33.6, lng: 73.04 },
  multan: { lat: 30.16, lng: 71.52 },
  islamabad: { lat: 33.68, lng: 73.04 },
  peshawar: { lat: 34.01, lng: 71.54 },
  quetta: { lat: 30.18, lng: 67.01 },
};

const MIN_LAT = 23.6;
const MAX_LAT = 37.1;
const MIN_LNG = 60.9;
const MAX_LNG = 77.8;
const PLACE_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function project(lat: number, lng: number) {
  return {
    x: ((lng - MIN_LNG) / (MAX_LNG - MIN_LNG)) * 100,
    y: ((MAX_LAT - lat) / (MAX_LAT - MIN_LAT)) * 100,
  };
}

function keyName(name: string) {
  return name.trim().toLowerCase();
}

function approachColor(approach: Approach, score: number | null) {
  const strength = score == null ? 0.5 : 0.35 + (score / 100) * 0.65;
  if (approach === "overlap") return `rgba(20, 138, 153, ${strength})`;
  if (approach === "investigate") return `rgba(245, 158, 11, ${strength})`;
  return `rgba(11, 79, 108, ${strength})`;
}

function approachLabel(approach: Approach) {
  if (approach === "overlap") return "Deepen — you serve this scored city";
  if (approach === "investigate") return "Investigate — scored, no placed orders";
  return "Serving — orders only, no market score";
}

function heatCities(brief: MarketBrief): HeatCity[] {
  const served = new Map((brief.served || []).map((row) => [keyName(row.city), row]));
  const scored = new Map((brief.scored || []).map((row) => [keyName(row.name), row]));
  const names = new Set([...served.keys(), ...scored.keys()]);
  const rows: HeatCity[] = [];
  names.forEach((name) => {
    const point = CITY_POINTS[name];
    if (!point) return;
    const scoreRow = scored.get(name);
    const servedRow = served.get(name);
    const approach: Approach = scoreRow && servedRow ? "overlap" : scoreRow ? "investigate" : "serving";
    const { x, y } = project(point.lat, point.lng);
    rows.push({
      id: scoreRow?.id || name,
      name: scoreRow?.name || servedRow?.city || name,
      score: scoreRow?.score ?? null,
      approach,
      x,
      y,
    });
  });
  return rows.sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
}

function bestApproaches(cities: HeatCity[]) {
  return [...cities]
    .sort((a, b) => {
      const rank = { overlap: 0, investigate: 1, serving: 2 };
      const delta = rank[a.approach] - rank[b.approach];
      if (delta !== 0) return delta;
      return (b.score ?? -1) - (a.score ?? -1);
    })
    .slice(0, 4);
}

export function MarketHeatmap({
  brief,
  open,
  onClose,
}: {
  brief: MarketBrief;
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const cities = useMemo(() => heatCities(brief), [brief]);
  const best = useMemo(() => bestApproaches(cities), [cities]);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogContent>
        <Stack spacing={2}>
          <Typography variant="h4">Market heatmap</Typography>
          <Typography variant="body2" color="text.secondary">
            Positions are geographic reference for catalog cities. Color uses stored scores and placed orders only. Empty cities are not heated.
          </Typography>
          {cities.length ? (
            <Box
              component="svg"
              viewBox="0 0 100 120"
              role="img"
              aria-label="Pakistan catalog cities colored by market approach"
              sx={{ width: "100%", height: { xs: 320, md: 440 }, bgcolor: "action.hover", borderRadius: 2 }}
            >
              <path
                d="M28 16 L46 10 L64 8 L78 16 L90 28 L93 46 L88 64 L78 82 L64 98 L48 108 L34 104 L22 90 L16 68 L18 44 L22 26 Z"
                fill="rgba(11,79,108,0.08)"
                stroke="rgba(11,79,108,0.28)"
                strokeWidth="0.6"
              />
              {cities.map((city) => {
                const radius = city.score == null ? 3.2 : 3.2 + (city.score / 100) * 4.2;
                return (
                  <g
                    key={city.id}
                    onClick={() => {
                      if (PLACE_ID.test(city.id)) {
                        router.push(`/app/markets/places/${city.id}`);
                        onClose();
                      }
                    }}
                    style={{ cursor: PLACE_ID.test(city.id) ? "pointer" : "default" }}
                  >
                    <circle cx={city.x} cy={city.y} r={radius + 3} fill={approachColor(city.approach, city.score)} opacity={0.28} />
                    <circle cx={city.x} cy={city.y} r={radius} fill={approachColor(city.approach, 100)} />
                    <text x={city.x} y={city.y + radius + 4.2} textAnchor="middle" fontSize="3.2" fill="currentColor">
                      {city.name}
                      {city.score != null ? ` ${city.score}` : ""}
                    </text>
                    <title>{`${city.name}: ${approachLabel(city.approach)}${city.score != null ? ` · ${city.score}/100` : ""}`}</title>
                  </g>
                );
              })}
            </Box>
          ) : (
            <EmptyState title="No cities to heat" description="Collect market sources or import orders first. The map does not invent city grades." />
          )}
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap" }}>
            <Typography variant="caption">Teal: deepen (serve + score)</Typography>
            <Typography variant="caption">Amber: investigate (score, no orders)</Typography>
            <Typography variant="caption">Navy: serving only</Typography>
          </Stack>
          {best.length ? (
            <Stack spacing={1}>
              <Typography variant="subtitle2">Best approach</Typography>
              {best.map((city) => (
                <Alert key={city.id} severity={city.approach === "overlap" ? "success" : city.approach === "investigate" ? "warning" : "info"}>
                  {city.name}
                  {city.score != null ? ` · ${city.score}/100` : ""} — {approachLabel(city.approach)}
                </Alert>
              ))}
            </Stack>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

export function MarketHeatmapButton({ brief }: { brief: MarketBrief | null }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="outlined" disabled={!brief} onClick={() => setOpen(true)}>
        Show heatmap
      </Button>
      {brief ? <MarketHeatmap brief={brief} open={open} onClose={() => setOpen(false)} /> : null}
    </>
  );
}
