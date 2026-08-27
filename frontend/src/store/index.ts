import { configureStore } from "@reduxjs/toolkit";
import createSagaMiddleware from "redux-saga";

import { dashboardReducer } from "@/store/slices/dashboardSlice";
import { authReducer } from "@/store/slices/authSlice";
import { tenantReducer } from "@/store/slices/tenantSlice";
import { uiReducer } from "@/store/slices/uiSlice";
import { rootSaga } from "@/store/rootSaga";

const sagaMiddleware = createSagaMiddleware();

export const store = configureStore({
  reducer: {
    auth: authReducer,
    tenant: tenantReducer,
    ui: uiReducer,
    dashboard: dashboardReducer,
  },
  middleware: (getDefault) => getDefault({ thunk: false }).concat(sagaMiddleware),
});

sagaMiddleware.run(rootSaga);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
