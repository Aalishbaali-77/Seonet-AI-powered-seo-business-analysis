import { call, put, takeLatest } from "redux-saga/effects";

import { dashboardApi, notificationApi } from "@/services/platformApi";
import {
  notificationsLoaded,
  notificationsRequested,
  overviewFailed,
  overviewRequested,
  overviewSucceeded,
} from "@/store/slices/dashboardSlice";
import type { DashboardOverview, NotificationItem } from "@/types/api";

function* loadOverview() {
  try {
    const data: DashboardOverview = yield call(dashboardApi.overview);
    yield put(overviewSucceeded(data));
  } catch (error) {
    yield put(overviewFailed(error instanceof Error ? error.message : "Unable to load dashboard."));
  }
}

function* loadNotifications() {
  try {
    const notifications: NotificationItem[] = yield call(notificationApi.list);
    yield put(notificationsLoaded(notifications ?? []));
  } catch {
    yield put(notificationsLoaded([]));
  }
}

export function* dashboardSaga() {
  yield takeLatest(overviewRequested.type, loadOverview);
  yield takeLatest(notificationsRequested.type, loadNotifications);
}
