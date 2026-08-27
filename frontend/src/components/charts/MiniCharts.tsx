"use client";

import { Box, Stack, Typography } from "@mui/material";

export function MiniBarChart({
  items,
  height = 140,
}: {
  items: Array<{ label: string; value: number }>;
  height?: number;
}) {
  const max = Math.max(...items.map((item) => item.value), 1);
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: "flex-end", height, width: "100%" }}>
      {items.map((item) => (
        <Stack key={item.label} spacing={0.5} sx={{ flex: 1, alignItems: "center", minWidth: 0, height: "100%", justifyContent: "flex-end" }}>
          <Typography variant="caption" color="text.secondary">
            {item.value}
          </Typography>
          <Box
            sx={{
              width: "100%",
              maxWidth: 48,
              height: `${Math.max(6, (item.value / max) * (height - 36))}px`,
              bgcolor: "primary.main",
              borderRadius: 1,
              opacity: 0.85,
            }}
          />
          <Typography variant="caption" noWrap sx={{ maxWidth: "100%" }}>
            {item.label}
          </Typography>
        </Stack>
      ))}
    </Stack>
  );
}

export function MiniLineChart({
  series,
  height = 160,
}: {
  series: Array<{ label: string; values: Array<number | null> }>;
  height?: number;
}) {
  const width = 560;
  const values = series.flatMap((item) => item.values.filter((value): value is number => value !== null));
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = Math.max(max - min, 1);
  const colors = ["#EA580C", "#0B4F6C", "#FBBF24"];
  return (
    <Box sx={{ overflowX: "auto" }}>
      <Box component="svg" viewBox={`0 0 ${width} ${height}`} sx={{ width: "100%", minWidth: 280, height }} role="img">
        {series.map((item, seriesIndex) => {
          const points = item.values
            .map((value, index) => {
              if (value === null) return null;
              const x = (index / Math.max(item.values.length - 1, 1)) * (width - 24) + 12;
              const y = height - 16 - ((value - min) / span) * (height - 32);
              return `${x},${y}`;
            })
            .filter(Boolean)
            .join(" ");
          return <polyline key={item.label} fill="none" stroke={colors[seriesIndex % colors.length]} strokeWidth="2.5" points={points} />;
        })}
      </Box>
      <Stack direction="row" spacing={2} sx={{ mt: 1, flexWrap: "wrap" }}>
        {series.map((item, index) => (
          <Typography key={item.label} variant="caption" sx={{ color: colors[index % colors.length] }}>
            {item.label}
          </Typography>
        ))}
      </Stack>
    </Box>
  );
}
