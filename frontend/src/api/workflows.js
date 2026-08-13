import { apiClient } from "./axiosClient";

export const workflowsApi = {
  run: (goal) => apiClient.post("/workflows/run", { goal }).then((res) => res.data),
};