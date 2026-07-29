import axios from "axios";
import { useAuthStore, type User } from "@/store/authStore";

const apiRoot =
  (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000")
    .replace(/\/api\/v1\/?$/, "");

type RefreshResponse = {
  access_token: string;
  refresh_token: string;
};

type UserProfile = {
  id: number;
  email: string;
  full_name?: string;
  role: string;
  is_active?: boolean;
  profile_completed?: boolean;
};

const api = axios.create({
  baseURL: `${apiRoot}/api/v1`,
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
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    // If 401 and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = typeof window !== "undefined" ? localStorage.getItem("refreshToken") : null;
        if (!refreshToken) {
          useAuthStore.getState().logout();
          return Promise.reject(error);
        }
        
        // Call refresh endpoint
        const { data } = await axios.post<RefreshResponse>(`${apiRoot}/api/v1/auth/refresh`, null, {
          headers: { "x-refresh-token": refreshToken }
        });
        
        // Update storage
        if (typeof window !== "undefined") {
          localStorage.setItem("accessToken", data.access_token);
          localStorage.setItem("refreshToken", data.refresh_token);
        }

        const profileRes = await axios.get<UserProfile>(`${apiRoot}/api/v1/users/me`, {
          headers: { Authorization: `Bearer ${data.access_token}` },
        });
        useAuthStore.getState().setAuth(profileRes.data as User, data.access_token);
        
        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout
        useAuthStore.getState().logout();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
