import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

import type { DashboardOverview, NotificationItem } from "@/types/api";

type DashboardState = {
  status: "idle" | "loading" | "ready" | "error";
  data: DashboardOverview | null;
  error: string | null;
  notifications: NotificationItem[];
};

const initialState: DashboardState = {
  status: "idle",
  data: null,
  error: null,
  notifications: [],
};

const dashboardSlice = createSlice({
  name: "dashboard",
  initialState,
  reducers: {
    overviewRequested: (state) => {
      state.status = "loading";
      state.error = null;
    },
    overviewSucceeded: (state, action: PayloadAction<DashboardOverview>) => {
      state.status = "ready";
      state.data = action.payload;
    },
    overviewFailed: (state, action: PayloadAction<string>) => {
      state.status = "error";
      state.error = action.payload;
    },
    notificationsLoaded: (state, action: PayloadAction<NotificationItem[]>) => {
      state.notifications = action.payload;
    },
    notificationsRequested: (_state) => {},
    notificationRead: (state, action: PayloadAction<{ id: string; read_at: string }>) => {
      const item = state.notifications.find((row) => row.id === action.payload.id);
      if (item) {
        item.read_at = action.payload.read_at;
      }
    },
  },
});

export const { overviewRequested, overviewSucceeded, overviewFailed, notificationsLoaded, notificationsRequested, notificationRead } =
  dashboardSlice.actions;
export const dashboardReducer = dashboardSlice.reducer;
