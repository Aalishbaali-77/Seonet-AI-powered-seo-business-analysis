"use client";

import type { ReactNode } from "react";
import { Box, Button, Stack, Typography } from "@mui/material";

import { BrandMark } from "@/components/branding/BrandMark";
import { useAppSelector } from "@/store/hooks";

export function PrintReportChrome({
  title,
  subtitle,
  children,
  actions,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  const branding = useAppSelector((state) => state.ui.branding);
  const tenant = useAppSelector((state) => state.tenant.items.find((item) => item.id === state.tenant.currentId));
  const printed = new Date().toLocaleString();

  return (
    <Stack spacing={3} className="seonet-print-root">
      <Box
        className="seonet-print-header"
        sx={{
          display: "none",
          "@media print": { display: "flex" },
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 2,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
        <BrandMark variant="nav" />
        <Box sx={{ textAlign: "right" }}>
          <Typography variant="h4">{title}</Typography>
          <Typography color="text.secondary">{tenant?.name || branding.legal_name}</Typography>
          <Typography variant="body2" color="text.secondary">
            {printed}
          </Typography>
        </Box>
      </Box>
      <Stack className="no-print" direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
        {actions}
        <Button variant="contained" onClick={() => window.print()}>
          Print
        </Button>
      </Stack>
      {children}
      <Box
        className="seonet-print-footer"
        sx={{
          display: "none",
          "@media print": { display: "flex" },
          flexDirection: "column",
          gap: 0.5,
          pt: 3,
          mt: 2,
          borderTop: 1,
          borderColor: "divider",
        }}
      >
        <Typography variant="body2">{branding.tagline || "Understand your business. Discover your market. Find your opportunities. Grow your sales."}</Typography>
        <Typography variant="body2" color="text.secondary">
          {branding.product_name} · {branding.legal_name} · Prepared for {tenant?.name || "this workspace"} · Not a public marketing prospectus; workspace intelligence report.
        </Typography>
        {branding.copyright_text ? (
          <Typography variant="body2" color="text.secondary">
            {branding.copyright_text}
          </Typography>
        ) : null}
      </Box>
    </Stack>
  );
}
