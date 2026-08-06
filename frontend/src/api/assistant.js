import { apiClient } from "./axiosClient";

export const assistantApi = {
    chat: (message, history = []) =>
        apiClient.post("/assistant/chat", { message, history }).then((res) => res.data),
};