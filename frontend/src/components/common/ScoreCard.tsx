"use client";

import { Card, CardContent, Typography } from "@mui/material";

import { ScoreRing, scoreRating } from "@/components/common/ScoreRing";

type ScoreCardProps = {
  label: string;
  value: number | null;
  hint?: string;
  onClick?: () => void;
};

export function ScoreCard({ label, value, hint, onClick }: ScoreCardProps) {
  return (
    <Card
      variant="outlined"
      sx={{ height: "100%", cursor: onClick ? "pointer" : "default" }}
      onClick={onClick}
    >
      <CardContent sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1, py: 2.25, px: 1.5 }}>
        <ScoreRing value={value} size={92} stroke={8} label={label} />
        <Typography variant="subtitle2" sx={{ textAlign: "center" }}>
          {label}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
          {hint ?? scoreRating(value)}
        </Typography>
      </CardContent>
    </Card>
  );
}
