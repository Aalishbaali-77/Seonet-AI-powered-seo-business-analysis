"use client";

import type { ReactNode } from "react";
import { Box, Card, CardContent, Typography } from "@mui/material";

type StatCardProps = {
  label: string;
  value: string | number;
  hint?: string;
  icon?: ReactNode;
  onClick?: () => void;
};

export function StatCard({ label, value, hint, icon, onClick }: StatCardProps) {
  return (
    <Card
      variant="outlined"
      sx={{ height: "100%", cursor: onClick ? "pointer" : "default" }}
      onClick={onClick}
    >
      <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
        <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 1 }}>
          <Typography variant="subtitle2" color="text.secondary">
            {label}
          </Typography>
          {icon}
        </Box>
        <Typography variant="h2" sx={{ mt: 1, fontSize: { xs: "1.35rem", md: "1.5rem" }, fontFamily: "var(--font-mono), ui-monospace, monospace", fontWeight: 500, letterSpacing: "-0.03em" }}>
          {value}
        </Typography>
        {hint ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {hint}
          </Typography>
        ) : null}
      </CardContent>
    </Card>
  );
}
