import { create } from "zustand";
import { api } from "../api/client";

const storedUser = localStorage.getItem("user");

export const useAuthStore = create((set) => ({
  token: localStorage.getItem("token"),
  user: storedUser ? JSON.parse(storedUser) : null,
  loading: false,
  async login(email, password) {
    set({ loading: true });
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    set({ token: data.access_token, user: data.user, loading: false });
  },
  async signup(payload) {
    set({ loading: true });
    const { data } = await api.post("/auth/signup", payload);
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    set({ token: data.access_token, user: data.user, loading: false });
  },
  logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    set({ token: null, user: null });
  }
}));
