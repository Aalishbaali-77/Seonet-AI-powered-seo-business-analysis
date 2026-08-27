"use client";

import { CssBaseline, ThemeProvider, useMediaQuery } from "@mui/material";
import { AppRouterCacheProvider } from "@mui/material-nextjs/v16-appRouter";
import { useEffect, useMemo } from "react";
import { Provider } from "react-redux";

import { BrandingApplier } from "@/components/branding/BrandingApplier";
import { ConfirmProvider } from "@/components/common/ConfirmDialog";
import { store } from "@/store";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { bootstrapRequested } from "@/store/slices/authSlice";
import { createSipulseTheme } from "@/theme/theme";

function Bootstrapper({ children }: { children: React.ReactNode }) {
  const dispatch = useAppDispatch();
  const status = useAppSelector((state) => state.auth.status);
  useEffect(() => {
    if (status === "idle") {
      dispatch(bootstrapRequested());
    }
  }, [dispatch, status]);
  return children;
}

function ThemedApp({ children }: { children: React.ReactNode }) {
  const preference = useAppSelector((state) => state.ui.themePreference);
  const branding = useAppSelector((state) => state.ui.branding);
  const systemDark = useMediaQuery("(prefers-color-scheme: dark)");
  const mode = preference === "system" ? (systemDark ? "dark" : "light") : preference;
  const theme = useMemo(
    () => createSipulseTheme(mode, { primary: branding.primary_color, secondary: branding.secondary_color }),
    [mode, branding.primary_color, branding.secondary_color],
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrandingApplier />
      <ConfirmProvider>{children}</ConfirmProvider>
    </ThemeProvider>
  );
}

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <AppRouterCacheProvider>
      <Provider store={store}>
        <ThemedApp>
          <Bootstrapper>{children}</Bootstrapper>
        </ThemedApp>
      </Provider>
    </AppRouterCacheProvider>
  );
}
