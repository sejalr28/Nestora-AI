import { apiClient } from "./axiosClient";

export const buildingsApi = {
  list: () => apiClient.get("/buildings").then((res) => res.data),
  create: (payload) => apiClient.post("/buildings", payload).then((res) => res.data),
};