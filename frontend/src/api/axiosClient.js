import axios from "axios";

/**
 * Single Axios instance for the whole dashboard. Every page/component
 * imports `apiClient` from here rather than importing axios directly --
 * keeps the base URL, timeout, and error normalization in one place.
 *
 * VITE_API_BASE_URL comes from frontend/.env (see .env.example). Vite only
 * exposes env vars prefixed with VITE_ to client code.
 */
export const apiClient = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
    timeout: 60000,
    headers: {
        "Content-Type": "application/json",
    },
});

// Normalizes every failed request into a plain Error with a readable
// message pulled from FastAPI's {"detail": "..."} error body, so page
// components can just do `catch (err) { setError(err.message) }` without
// knowing anything about Axios's error shape.
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        const detail = error.response?.data?.detail;
        const message =
            (typeof detail === "string" && detail) ||
            error.message ||
            "Something went wrong talking to the server.";
        return Promise.reject(new Error(message));
    }
);