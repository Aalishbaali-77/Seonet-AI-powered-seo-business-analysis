"use client";

import { Chip } from "@mui/material";

const tones: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
  active: "success",
  success: "success",
  partial: "warning",
  failed: "error",
  paid: "success",
  issued: "info",
  trialing: "info",
  pending: "warning",
  past_due: "warning",
  overdue: "warning",
  suspended: "error",
  canceled: "default",
  void: "default",
  draft: "default",
  archived: "default",
  disconnected: "warning",
  configured: "info",
  connected: "success",
  error: "error",
  available: "success",
  info: "info",
  new: "info",
  qualified: "success",
  contacted: "warning",
  unqualified: "default",
  open: "info",
  reviewing: "warning",
  accepted: "success",
  dismissed: "default",
  sent: "info",
  ready: "success",
};

export function StatusChip({ value }: { value: string }) {
  const color = tones[value] ?? "default";
  return <Chip size="small" color={color} label={value.replace(/_/g, " ")} sx={{ textTransform: "capitalize" }} />;
}
