import { apiClient } from "./axiosClient";

export const waterScheduleApi = {
  list: () => apiClient.get("/water-schedule").then((res) => res.data),
  update: (source, payload) => apiClient.put(`/water-schedule/${source}`, payload).then((res) => res.data),
};