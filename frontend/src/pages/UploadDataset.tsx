import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiGet } from "../api/client";
import { uploadDataset, type UploadDatasetResponse } from "../lib/api";

type UploadMode = "create" | "existing";

type DatasetOption = {
  id: string;
  name: string;
};

export default function UploadDataset() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<UploadMode>("create");
  const [datasetName, setDatasetName] = useState("");
  const [description, setDescription] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [datasets, setDatasets] = useState<DatasetOption[]>([]);
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [datasetsError, setDatasetsError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDatasets() {
      if (mode !== "existing") return;
      setDatasetsLoading(true);
      setDatasetsError(null);
      try {
        const rows = await apiGet<DatasetOption[]>("/datasets");
        if (!cancelled) {
          setDatasets(rows);
          if (rows.length > 0) {
            setDatasetId((prev) => (prev ? prev : rows[0].id));
          }
        }
      } catch (err: any) {
        if (!cancelled) {
          setDatasetsError(err?.message || "Failed to load datasets.");
        }
      } finally {
        if (!cancelled) {
          setDatasetsLoading(false);
        }
      }
    }

    loadDatasets();
    return () => {
      cancelled = true;
    };
  }, [mode]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    if (!file) {
      setError("CSV file is required.");
      return;
    }

    if (mode === "create" && !datasetName.trim()) {
      setError("Dataset name and CSV file are required.");
      return;
    }

    if (mode === "existing" && !datasetId) {
      setError("Please select an existing dataset.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const result: UploadDatasetResponse =
        mode === "create"
          ? await uploadDataset({
              dataset_name: datasetName.trim(),
              description,
              file,
            })
          : await uploadDataset({
              dataset_id: datasetId,
              file,
            });
      const uploadedDatasetId = result.dataset_id;
      navigate(`/datasets/${uploadedDatasetId}`);
    } catch (err: any) {
      setError(err.message || "Upload failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl p-6">
      <h1 className="mb-4 text-xl font-semibold text-white">Upload Dataset</h1>
      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-white/10 bg-white/5 p-6"
      >
        <div>
          <label className="mb-2 block text-sm text-white/70">Upload Mode</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => {
                setMode("create");
                setError(null);
              }}
              className={`rounded border px-3 py-2 text-sm transition ${
                mode === "create"
                  ? "border-blue-500 bg-blue-600 text-white"
                  : "border-white/10 bg-black/30 text-white"
              }`}
            >
              Create New Dataset
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("existing");
                setError(null);
              }}
              className={`rounded border px-3 py-2 text-sm transition ${
                mode === "existing"
                  ? "border-blue-500 bg-blue-600 text-white"
                  : "border-white/10 bg-black/30 text-white"
              }`}
            >
              Use Existing Dataset
            </button>
          </div>
        </div>

        {mode === "create" ? (
          <>
            <div>
              <label className="mb-1 block text-sm text-white/70">
                Dataset Name *
              </label>
              <input
                type="text"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                className="w-full rounded border border-white/10 bg-black/30 px-3 py-2 text-white"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm text-white/70">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded border border-white/10 bg-black/30 px-3 py-2 text-white"
              />
            </div>
          </>
        ) : (
          <div>
            <label className="mb-1 block text-sm text-white/70">
              Existing Dataset *
            </label>
            <select
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
              className="w-full rounded border border-white/10 bg-black/30 px-3 py-2 text-white"
              disabled={datasetsLoading || datasets.length === 0}
            >
              {datasets.length === 0 ? (
                <option value="">
                  {datasetsLoading ? "Loading datasets..." : "No datasets available"}
                </option>
              ) : null}
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
            {datasetsError ? (
              <div className="mt-2 text-sm text-red-400">{datasetsError}</div>
            ) : null}
          </div>
        )}

        <div>
          <label className="mb-1 block text-sm text-white/70">CSV File *</label>
          <input
            type="file"
            accept=".csv"
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                setFile(e.target.files[0]);
              }
            }}
            className="text-white"
          />
        </div>

        {error && <div className="text-sm text-red-400">{error}</div>}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-blue-600 py-2 text-white transition hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Uploading..." : "Upload Dataset"}
        </button>
      </form>
    </div>
  );
}
