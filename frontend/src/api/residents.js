import { apiClient } from "./axiosClient";

export const residentsApi = {
  list: () => apiClient.get("/residents").then((res) => res.data),
  create: (payload) => apiClient.post("/residents", payload).then((res) => res.data),
  update: (residentId, payload) => apiClient.patch(`/residents/${residentId}`, payload).then((res) => res.data),
};