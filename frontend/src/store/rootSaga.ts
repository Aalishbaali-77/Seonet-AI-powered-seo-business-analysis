import { all } from "redux-saga/effects";

import { authSaga } from "@/store/sagas/authSaga";
import { dashboardSaga } from "@/store/sagas/dashboardSaga";

export function* rootSaga() {
  yield all([authSaga(), dashboardSaga()]);
}
