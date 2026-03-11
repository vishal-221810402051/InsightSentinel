import axios from "axios";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;

export type UploadDatasetPayload =
  | {
      file: File;
      dataset_name: string;
      description?: string;
    }
  | {
      file: File;
      dataset_id: string;
      description?: string;
    };

export type UploadDatasetResponse = {
  dataset_id: string;
  snapshot_id: string;
  run_id: string;
  row_count: number;
  column_count: number;
  status: string;
  message: string;
  alerts_created: number;
  name?: string;
  description?: string;
  duration_ms?: number;
};

export async function uploadDataset(
  payload: UploadDatasetPayload
): Promise<UploadDatasetResponse> {
  const token = localStorage.getItem("access_token");
  const formData = new FormData();

  if ("dataset_id" in payload) {
    formData.append("dataset_id", payload.dataset_id);
    if (payload.description) {
      formData.append("description", payload.description);
    }
  } else {
    formData.append("dataset_name", payload.dataset_name);
    formData.append("description", payload.description ?? "");
  }
  formData.append("file", payload.file);

  const res = await fetch(
    `${process.env.REACT_APP_API_BASE_URL || "http://localhost:8000"}/ingest/csv`,
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    }
  );

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Upload failed");
  }

  return res.json() as Promise<UploadDatasetResponse>;
}
