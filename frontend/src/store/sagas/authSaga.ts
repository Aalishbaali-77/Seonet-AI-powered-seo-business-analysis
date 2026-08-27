import { call, put, select, takeLatest } from "redux-saga/effects";

import { authApi } from "@/services/authApi";
import { configApi } from "@/services/platformApi";
import {
  authCleared,
  authFailed,
  authSucceeded,
  bootstrapRequested,
  loginRequested,
  logoutRequested,
  registerRequested,
} from "@/store/slices/authSlice";
import { tenantsHydrated } from "@/store/slices/tenantSlice";
import { brandingSet, catalogSet, featureFlagsSet, landingSet, themePreferenceSet } from "@/store/slices/uiSlice";
import type { CurrentUser, PlatformBranding, PublicConfig } from "@/types/api";
import { defaultBranding, defaultLanding } from "@/types/api";
import type { RootState } from "@/store";

function applyConfig(config: PublicConfig) {
  const branding: PlatformBranding = { ...defaultBranding, ...config.branding };
  return {
    branding,
    flags: config.feature_flags ?? {},
    landing: { ...defaultLanding, ...config.landing },
    packages: config.packages ?? [],
    modules: config.modules ?? [],
  };
}

function* hydrateUser(user: CurrentUser) {
  yield put(authSucceeded(user));
  yield put(tenantsHydrated(user.tenants));
  yield put(themePreferenceSet(user.theme_preference));
}

function* bootstrap() {
  try {
    const config: PublicConfig = yield call(configApi.get);
    const { branding, flags, landing, packages, modules } = applyConfig(config);
    yield put(featureFlagsSet(flags));
    yield put(brandingSet(branding));
    yield put(landingSet(landing));
    yield put(catalogSet({ packages, modules }));
    yield put(themePreferenceSet(branding.default_theme));
  } catch {
    // Keep compiled defaults when public config is unavailable.
  }
  try {
    const user: CurrentUser = yield call(authApi.me);
    yield* hydrateUser(user);
  } catch {
    yield put(authCleared());
  }
}

function* login(action: ReturnType<typeof loginRequested>) {
  try {
    const user: CurrentUser = yield call(authApi.login, action.payload);
    yield* hydrateUser(user);
  } catch (error) {
    yield put(authFailed(error instanceof Error ? error.message : "Unable to sign in."));
  }
}

function* register(action: ReturnType<typeof registerRequested>) {
  try {
    const user: CurrentUser = yield call(authApi.register, action.payload);
    yield* hydrateUser(user);
  } catch (error) {
    yield put(authFailed(error instanceof Error ? error.message : "Unable to create your workspace."));
  }
}

function* logout() {
  try {
    yield call(authApi.logout);
  } finally {
    yield put(authCleared());
    const branding: PlatformBranding = yield select((state: RootState) => state.ui.branding);
    yield put(themePreferenceSet(branding.default_theme));
  }
}

export function* authSaga() {
  yield takeLatest(bootstrapRequested.type, bootstrap);
  yield takeLatest(loginRequested.type, login);
  yield takeLatest(registerRequested.type, register);
  yield takeLatest(logoutRequested.type, logout);
}
