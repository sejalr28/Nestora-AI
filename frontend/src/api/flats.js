import { apiClient } from "./axiosClient";

export const flatsApi = {
  listByBuilding: (buildingId) =>
    apiClient.get("/flats", { params: { building_id: buildingId } }).then((res) => res.data),
  create: (payload) => apiClient.post("/flats", payload).then((res) => res.data),
  update: (flatId, payload) => apiClient.patch(`/flats/${flatId}`, payload).then((res) => res.data),
};