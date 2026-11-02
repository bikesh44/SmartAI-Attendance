import api, { clearApiCache } from "./api";

export async function login(credentials) {
  clearApiCache();
  const response = await api.post("/auth/login", credentials);
  return response.data;
}

export async function logout() {
  try {
    const response = await api.post("/auth/logout");
    return response.data;
  } finally {
    clearApiCache();
  }
}

export async function getCurrentUser() {
  const response = await api.get("/auth/me");
  return response.data;
}