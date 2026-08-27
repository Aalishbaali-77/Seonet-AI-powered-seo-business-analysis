"use client";

import { createTheme, darken, lighten, type PaletteMode } from "@mui/material/styles";

import { breakpoints } from "./breakpoints";
import { colors } from "./colors";
import { components } from "./components";
import { spacing } from "./spacing";
import { typography } from "./typography";

const HEX = /^#[0-9A-Fa-f]{6}$/;

function hex(value: string | undefined, fallback: string) {
  return value && HEX.test(value) ? value : fallback;
}

export function createSeonetTheme(mode: PaletteMode, brand?: { primary?: string; secondary?: string }) {
  const surface = mode === "light" ? colors.light : colors.dark;
  const primary = hex(brand?.primary, colors.brand.navy);
  const secondary = hex(brand?.secondary, colors.brand.teal);
  return createTheme({
    palette: {
      mode,
      primary: {
        main: primary,
        dark: darken(primary, 0.18),
        light: lighten(primary, 0.18),
        contrastText: "#FFFFFF",
      },
      secondary: {
        main: secondary,
        dark: darken(secondary, 0.16),
        contrastText: "#FFFFFF",
      },
      success: { main: colors.semantic.success },
      warning: { main: colors.semantic.warning },
      error: { main: colors.semantic.error },
      info: { main: primary },
      background: {
        default: surface.background,
        paper: surface.paper,
      },
      text: {
        primary: surface.textPrimary,
        secondary: surface.textSecondary,
      },
      divider: surface.border,
    },
    typography,
    spacing,
    breakpoints,
    shape: { borderRadius: 12 },
    components,
  });
}
