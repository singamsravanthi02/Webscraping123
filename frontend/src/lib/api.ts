import axios from "axios";
import { useAuthStore } from "@/store/authStore";

const apiRoot = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/api\/v1\/?$/, "");

const api = axios.create({
  baseURL: `${apiRoot}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token =
      useAuthStore.getState().accessToken ||
      (typeof window !== "undefined" ? localStorage.getItem("accessToken") : null);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
