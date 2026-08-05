import { apiClient } from "./axiosClient";

export const vendorsApi = {
  list: ({ category, activeOnly = true } = {}) =>
    apiClient
      .get("/vendors", { params: { category: category || undefined, active_only: activeOnly } })
      .then((res) => res.data),
  create: (payload) => apiClient.post("/vendors", payload).then((res) => res.data),
  update: (vendorId, payload) => apiClient.patch(`/vendors/${vendorId}`, payload).then((res) => res.data),
};