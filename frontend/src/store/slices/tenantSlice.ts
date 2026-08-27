import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

import type { TenantSummary } from "@/types/api";

type TenantState = {
  currentId: string | null;
  items: TenantSummary[];
};

const initialState: TenantState = {
  currentId: null,
  items: [],
};

const tenantSlice = createSlice({
  name: "tenant",
  initialState,
  reducers: {
    tenantsHydrated: (state, action: PayloadAction<TenantSummary[]>) => {
      state.items = action.payload;
      const stored = typeof window !== "undefined" ? window.localStorage.getItem("seonet.tenant") : null;
      const match = action.payload.find((item) => item.id === stored);
      const preferred = match ?? action.payload.find((item) => item.is_default) ?? action.payload[0];
      if (preferred) {
        state.currentId = preferred.id;
        if (typeof window !== "undefined") {
          window.localStorage.setItem("seonet.tenant", preferred.id);
        }
      }
    },
    tenantSelected: (state, action: PayloadAction<string>) => {
      state.currentId = action.payload;
      if (typeof window !== "undefined") {
        window.localStorage.setItem("seonet.tenant", action.payload);
      }
    },
  },
});

export const { tenantsHydrated, tenantSelected } = tenantSlice.actions;
export const tenantReducer = tenantSlice.reducer;
