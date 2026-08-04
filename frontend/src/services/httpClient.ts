import axios from "axios";

export const httpClient = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
    timeout: 20000,
});

httpClient.interceptors.response.use(
    (response) => response,
    (error) => {
        const detail = error.response?.data?.detail;
        const message = typeof detail === "string"
            ? detail
            : "Unable to complete the request. Please try again.";

        return Promise.reject(new Error(message));
    },
);
