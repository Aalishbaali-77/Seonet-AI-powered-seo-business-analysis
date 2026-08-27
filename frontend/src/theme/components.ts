import type { Components, Theme } from "@mui/material/styles";

import { fonts } from "./typography";

export const components: Components<Theme> = {
  MuiCssBaseline: {
    styleOverrides: {
      html: {
        WebkitFontSmoothing: "antialiased",
        MozOsxFontSmoothing: "grayscale",
      },
      body: {
        fontFeatureSettings: '"kern", "liga", "calt"',
      },
      code: { fontFamily: fonts.mono },
      kbd: { fontFamily: fonts.mono },
      pre: { fontFamily: fonts.mono },
    },
  },
  MuiButton: {
    defaultProps: { disableElevation: true },
    styleOverrides: {
      root: {
        borderRadius: 10,
        paddingInline: 16,
        minHeight: 40,
      },
      sizeLarge: { minHeight: 46, paddingInline: 20 },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 16,
        backgroundImage: "none",
      },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: { backgroundImage: "none" },
    },
  },
  MuiTextField: {
    defaultProps: { size: "small", fullWidth: true },
  },
  MuiChip: {
    styleOverrides: {
      root: { borderRadius: 8, fontWeight: 650 },
    },
  },
  MuiDrawer: {
    styleOverrides: {
      paper: { borderRight: "none" },
    },
  },
  MuiTooltip: {
    defaultProps: { arrow: true },
  },
  MuiAppBar: {
    styleOverrides: {
      root: { backgroundImage: "none" },
    },
  },
  MuiDialog: {
    styleOverrides: {
      paper: { borderRadius: 16 },
    },
  },
  MuiDialogTitle: {
    styleOverrides: {
      root: {
        fontWeight: 700,
        fontSize: "1.125rem",
      },
    },
  },
  MuiDialogActions: {
    styleOverrides: {
      root: {
        padding: "12px 24px 20px",
      },
    },
  },
};
