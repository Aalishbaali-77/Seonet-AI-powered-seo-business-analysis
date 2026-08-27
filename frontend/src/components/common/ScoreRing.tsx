"use client";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlined";
import { Box, Typography } from "@mui/material";
import { useId } from "react";

export function scoreRating(value: number | null) {
  if (value === null) {
    return "No score";
  }
  if (value >= 90) {
    return "Excellent";
  }
  if (value >= 75) {
    return "Strong";
  }
  if (value >= 60) {
    return "Fair";
  }
  if (value >= 40) {
    return "Needs work";
  }
  return "Critical";
}

export function scoreGradient(value: number | null) {
  if (value === null) {
    return { from: "#7A8B9C", to: "#5A6B7C" };
  }
  if (value >= 90) {
    return { from: "#FED7AA", to: "#EA580C" };
  }
  if (value >= 75) {
    return { from: "#38BDF8", to: "#0B4F6C" };
  }
  if (value >= 60) {
    return { from: "#FBBF24", to: "#B7791F" };
  }
  if (value >= 40) {
    return { from: "#FB923C", to: "#C2410C" };
  }
  return { from: "#F87171", to: "#C0392B" };
}

const TONE_GRADIENT = {
  progress: { from: "#FED7AA", to: "#EA580C" },
  error: { from: "#F87171", to: "#C0392B" },
};

export function ScoreRing({
  value,
  size = 96,
  stroke = 8,
  label,
  tone = "auto",
  suffix,
  icon,
}: {
  value: number | null;
  size?: number;
  stroke?: number;
  label?: string;
  tone?: "auto" | "progress" | "error";
  suffix?: string;
  icon?: "check" | "error";
}) {
  const gradientId = useId().replace(/:/g, "");
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = value === null ? 0 : Math.max(0, Math.min(100, value));
  const offset = circumference - (pct / 100) * circumference;
  const { from, to } = tone === "auto" ? scoreGradient(value) : TONE_GRADIENT[tone];
  const fontSize = size >= 140 ? size * 0.26 : size * 0.24;

  return (
    <Box sx={{ width: size, height: size, position: "relative", flexShrink: 0 }}>
      <Box
        component="svg"
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        sx={{ display: "block", transform: "rotate(-90deg)" }}
        aria-label={label ? `${label} ${value ?? "unavailable"}` : `Score ${value ?? "unavailable"}`}
      >
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={from} />
            <stop offset="100%" stopColor={to} />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth={stroke} opacity={0.12} />
        <Box
          component="circle"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          sx={{ transition: "stroke-dashoffset 0.6s cubic-bezier(0.4, 0, 0.2, 1)" }}
        />
      </Box>
      <Box sx={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
        {icon === "check" ? (
          <CheckCircleIcon sx={{ fontSize: size * 0.42, color: to }} />
        ) : icon === "error" ? (
          <ErrorOutlineIcon sx={{ fontSize: size * 0.42, color: to }} />
        ) : (
          <>
            <Typography sx={{ fontWeight: 700, fontSize, letterSpacing: "-0.05em", lineHeight: 1, color: to }}>
              {value === null ? "—" : Math.round(value)}
            </Typography>
            {suffix && value !== null ? (
              <Typography component="span" sx={{ fontWeight: 700, fontSize: fontSize * 0.38, color: to, ml: 0.2, mt: 0.6 }}>
                {suffix}
              </Typography>
            ) : null}
          </>
        )}
      </Box>
    </Box>
  );
}
