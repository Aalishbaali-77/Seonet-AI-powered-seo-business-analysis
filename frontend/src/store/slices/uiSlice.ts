import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

import { defaultBranding, defaultLanding, type LandingContent, type PlanPackage, type PlatformBranding, type ProductModule } from "@/types/api";

type ThemePreference = "light" | "dark" | "system";

type UiState = {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  commandOpen: boolean;
  themePreference: ThemePreference;
  featureFlags: Record<string, boolean>;
  branding: PlatformBranding;
  landing: LandingContent;
  packages: PlanPackage[];
  modules: ProductModule[];
};

const initialState: UiState = {
  sidebarOpen: false,
  sidebarCollapsed: false,
  commandOpen: false,
  themePreference: "light",
  featureFlags: {},
  branding: defaultBranding,
  landing: defaultLanding,
  packages: [],
  modules: [],
};

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    sidebarToggled: (state, action: PayloadAction<boolean | undefined>) => {
      state.sidebarOpen = action.payload ?? !state.sidebarOpen;
    },
    sidebarCollapsedToggled: (state, action: PayloadAction<boolean | undefined>) => {
      state.sidebarCollapsed = action.payload ?? !state.sidebarCollapsed;
    },
    commandToggled: (state, action: PayloadAction<boolean | undefined>) => {
      state.commandOpen = action.payload ?? !state.commandOpen;
    },
    themePreferenceSet: (state, action: PayloadAction<ThemePreference>) => {
      state.themePreference = action.payload;
    },
    featureFlagsSet: (state, action: PayloadAction<Record<string, boolean>>) => {
      state.featureFlags = action.payload;
    },
    brandingSet: (state, action: PayloadAction<PlatformBranding>) => {
      state.branding = action.payload;
    },
    landingSet: (state, action: PayloadAction<LandingContent>) => {
      state.landing = action.payload;
    },
    catalogSet: (state, action: PayloadAction<{ packages: PlanPackage[]; modules: ProductModule[] }>) => {
      state.packages = action.payload.packages;
      state.modules = action.payload.modules;
    },
  },
});

export const {
  sidebarToggled,
  sidebarCollapsedToggled,
  commandToggled,
  themePreferenceSet,
  featureFlagsSet,
  brandingSet,
  landingSet,
  catalogSet,
} = uiSlice.actions;
export const uiReducer = uiSlice.reducer;
