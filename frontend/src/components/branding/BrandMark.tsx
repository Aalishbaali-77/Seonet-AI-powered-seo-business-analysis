"use client";

import { Box, Typography, useTheme } from "@mui/material";

import { useAppSelector } from "@/store/hooks";
import type { PlatformBranding } from "@/types/api";

export const DEFAULT_LOGO = "/logo.png";
export const DEFAULT_FAVICON = "/favicon.png";

type BrandMarkVariant = "nav" | "sidebar" | "footer" | "collapsed";

function productInitials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase() || "SP";
}

function pair(mode: "light" | "dark", light: string | null | undefined, dark: string | null | undefined) {
  const preferred = mode === "dark" ? dark || light : light || dark;
  return preferred || null;
}

export function resolveBrandSrc(branding: PlatformBranding, slot: BrandMarkVariant, mode: "light" | "dark") {
  const master = pair(mode, branding.logo_url, branding.logo_dark_url);
  const mark = pair(mode, branding.logo_mark_url, branding.logo_mark_dark_url);
  if (slot === "nav") {
    return pair(mode, branding.logo_nav_url, branding.logo_nav_dark_url) || master;
  }
  if (slot === "sidebar") {
    return pair(mode, branding.logo_sidebar_url, branding.logo_sidebar_dark_url) || master;
  }
  if (slot === "footer") {
    return pair(mode, branding.logo_footer_url, branding.logo_footer_dark_url) || master;
  }
  return mark || pair(mode, branding.logo_nav_url, branding.logo_nav_dark_url) || master;
}

export function resolveFaviconSrc(branding: PlatformBranding) {
  return branding.favicon_url || branding.app_icon_url || branding.logo_mark_url || null;
}

export function BrandMark({
  collapsed = false,
  subtitle,
  variant,
}: {
  collapsed?: boolean;
  subtitle?: string;
  variant?: BrandMarkVariant;
}) {
  const branding = useAppSelector((state) => state.ui.branding);
  const theme = useTheme();
  const mode = theme.palette.mode;
  const slot: BrandMarkVariant = variant ?? (collapsed ? "collapsed" : "sidebar");
  const uploaded = resolveBrandSrc(branding, slot, mode);
  const src = uploaded || DEFAULT_LOGO;
  const usingFallback = !uploaded;

  const frame = {
    nav: { height: { xs: 40, md: 44 }, maxWidth: { xs: 132, sm: 168 } },
    sidebar: { height: 42, maxWidth: 176 },
    footer: { height: 56, maxWidth: 196 },
    collapsed: { height: 36, maxWidth: 36 },
  }[slot];

  const mark = (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: frame.height,
        maxWidth: frame.maxWidth,
        borderRadius: slot === "collapsed" ? 1.25 : 1.5,
        overflow: "hidden",
        flexShrink: 0,
        bgcolor: usingFallback ? "#081018" : "transparent",
        border: usingFallback ? 1 : 0,
        borderColor: usingFallback ? "divider" : "transparent",
        boxShadow: usingFallback ? "0 1px 2px rgba(15, 27, 45, 0.08)" : "none",
      }}
    >
      <Box
        component="img"
        src={src}
        alt={branding.product_name}
        sx={{
          height: "100%",
          width: "auto",
          maxWidth: "100%",
          objectFit: "contain",
          objectPosition: slot === "collapsed" && usingFallback ? "center top" : "center",
          display: "block",
        }}
      />
    </Box>
  );

  if (slot === "collapsed" || !subtitle) {
    return mark;
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", minWidth: 0 }}>
      {mark}
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1, lineHeight: 1.35 }}>
        {subtitle}
      </Typography>
    </Box>
  );
}
