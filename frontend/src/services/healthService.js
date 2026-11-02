import api from "./api";

export async function getHealthStatus() {
  const response = await api.get("/health");
  return response.data;
}