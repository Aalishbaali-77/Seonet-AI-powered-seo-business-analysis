import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

import type { CurrentUser } from "@/types/api";

type AuthState = {
  user: CurrentUser | null;
  status: "idle" | "loading" | "authenticated" | "unauthenticated";
  submitting: boolean;
  error: string | null;
};

const initialState: AuthState = {
  user: null,
  status: "idle",
  submitting: false,
  error: null,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    bootstrapRequested: (state) => {
      state.status = "loading";
      state.error = null;
    },
    loginRequested: (state, _action: PayloadAction<{ email: string; password: string }>) => {
      state.submitting = true;
      state.error = null;
    },
    registerRequested: (
      state,
      _action: PayloadAction<{ email: string; password: string; name?: string; first_name?: string; last_name?: string; company_name?: string }>,
    ) => {
      state.submitting = true;
      state.error = null;
    },
    logoutRequested: () => undefined,
    authSucceeded: (state, action: PayloadAction<CurrentUser>) => {
      state.user = action.payload;
      state.status = "authenticated";
      state.submitting = false;
      state.error = null;
    },
    authFailed: (state, action: PayloadAction<string>) => {
      state.user = null;
      state.status = "unauthenticated";
      state.submitting = false;
      state.error = action.payload;
    },
    authCleared: (state) => {
      state.user = null;
      state.status = "unauthenticated";
      state.submitting = false;
      state.error = null;
    },
  },
});

export const {
  bootstrapRequested,
  loginRequested,
  registerRequested,
  logoutRequested,
  authSucceeded,
  authFailed,
  authCleared,
} = authSlice.actions;

export const authReducer = authSlice.reducer;
