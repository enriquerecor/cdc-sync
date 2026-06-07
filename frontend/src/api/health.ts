import { apiClient } from "./client";

export async function getHealthStatus() {
  const { data, error } = await apiClient.GET("/health");

  if (error) {
    throw error;
  }

  return data;
}
