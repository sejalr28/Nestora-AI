import { apiClient } from "./axiosClient";

export const serviceRequestsApi = {
  list: ({ status } = {}) =>
    apiClient.get("/service-requests", { params: { status: status || undefined } }).then((res) => res.data),
  create: (payload) => apiClient.post("/service-requests", payload).then((res) => res.data),
  update: (requestId, payload) =>
    apiClient.patch(`/service-requests/${requestId}`, payload).then((res) => res.data),
};