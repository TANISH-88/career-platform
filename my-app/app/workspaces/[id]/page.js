"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import Features from "../../components/Features";
import ResumeUpload from "../../components/ResumeUpload";
import { useAuth } from "../../components/AuthContext";
import { ORDERED_SKILL_KEYS, valuesArrayToMap } from "../../../lib/continuePopupLogic.mjs";

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function WorkspaceDetailPage() {
  const params = useParams();
  const workspaceId = typeof params?.id === "string" ? params.id : "";

  const { api, isAuthenticated, isLoading, refreshLastActive } = useAuth();

  const [workspace, setWorkspace] = useState(null);
  const [history, setHistory] = useState([]);
  const [values, setValues] = useState({});
  const [prediction, setPrediction] = useState(null);
  const [predictError, setPredictError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [predicting, setPredicting] = useState(false);

  const loadWorkspaceData = useCallback(async () => {
    if (!workspaceId) return;
    setLoadingData(true);
    setLoadError("");
    setNotFound(false);
    try {
      const [ws, hist] = await Promise.all([
        api.getWorkspace(workspaceId),
        api.getWorkspaceHistory(workspaceId),
      ]);
      setWorkspace(ws);
      setHistory(hist);
      if (hist.length > 0 && Array.isArray(hist[0].values)) {
        setValues(valuesArrayToMap(hist[0].values));
      }
      await refreshLastActive();
    } catch (err) {
      if (err?.status === 404) {
        setNotFound(true);
      } else {
        setLoadError(err.message || "Failed to load workspace");
      }
    } finally {
      setLoadingData(false);
    }
  }, [api, workspaceId, refreshLastActive]);

  useEffect(() => {
    if (!isLoading && isAuthenticated && workspaceId) {
      loadWorkspaceData();
    }
  }, [isAuthenticated, isLoading, workspaceId, loadWorkspaceData]);

  async function handleWorkspacePredict() {
    setPredictError("");
    const finalValues = ORDERED_SKILL_KEYS.map((key) => {
      const rawValue = values[key];
      return rawValue === "" || rawValue === undefined ? NaN : Number(rawValue);
    });

    if (finalValues.some((v) => !Number.isFinite(v))) {
      setPredictError("Enter a number for every field (1-10).");
      return;
    }

    setPredicting(true);
    try {
      const res = await api.predictInWorkspace(workspaceId, finalValues);
      setPrediction(res);
      const updatedHistory = await api.getWorkspaceHistory(workspaceId);
      setHistory(updatedHistory);
      await refreshLastActive();
    } catch (err) {
      if (err?.status === 404) {
        setNotFound(true);
      } else {
        setPredictError(err.message || "Prediction failed");
      }
    } finally {
      setPredicting(false);
    }
  }

  async function handleRestore() {
    try {
      const updated = await api.unarchiveWorkspace(workspaceId);
      setWorkspace(updated);
      await refreshLastActive();
    } catch (err) {
      setLoadError(err.message || "Could not restore workspace");
    }
  }

  if (isLoading || (isAuthenticated && loadingData && !workspace && !notFound && !loadError)) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-16 text-center text-gray-600">
        Loading workspace...
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="px-6 py-16">
        <div className="mx-auto max-w-lg rounded-3xl border border-gray-200 bg-white/85 p-8 text-center shadow-2xl backdrop-blur">
          <h2 className="text-2xl font-bold text-gray-900">Sign in required</h2>
          <p className="mt-2 text-sm text-gray-600">
            Workspaces are private to your account. Sign in to continue working here.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link
              href="/login"
              className="rounded-xl bg-black px-5 py-2.5 text-sm font-semibold text-white hover:bg-gray-800"
            >
              Sign in
            </Link>
            <Link
              href="/"
              className="rounded-xl border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              Anonymous Predict
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (notFound) {
    return (
      <main className="px-6 py-16">
        <div className="mx-auto max-w-lg rounded-3xl border border-gray-200 bg-white/85 p-8 text-center shadow-2xl backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500">404</p>
          <h2 className="mt-2 text-2xl font-bold text-gray-900">Workspace not found</h2>
          <p className="mt-2 text-sm text-gray-600">
            This workspace does not exist or you do not have access to it.
          </p>
          <Link
            href="/workspaces"
            className="mt-6 inline-block rounded-xl bg-black px-5 py-2.5 text-sm font-semibold text-white hover:bg-gray-800"
          >
            Back to workspaces
          </Link>
        </div>
      </main>
    );
  }

  if (loadError) {
    return (
      <main className="px-6 py-16">
        <div className="mx-auto max-w-lg rounded-3xl border border-red-200 bg-white p-8 text-center shadow-lg">
          <p className="text-sm text-red-700">{loadError}</p>
          <Link
            href="/workspaces"
            className="mt-4 inline-block rounded-xl bg-black px-5 py-2.5 text-sm font-semibold text-white"
          >
            Back to workspaces
          </Link>
        </div>
      </main>
    );
  }

  return (
    <div className="pb-16">
      <div className="mx-auto max-w-5xl px-6 pt-8">
        <div className="rounded-3xl border border-gray-200 bg-white/85 p-6 shadow-xl backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <Link
                href="/workspaces"
                className="text-xs font-semibold uppercase tracking-[0.25em] text-indigo-600 hover:underline"
              >
                ← All Workspaces
              </Link>
              <h2 className="mt-1 text-3xl font-bold text-gray-900">
                {workspace?.name || "Workspace"}
              </h2>
              {workspace?.last_opened_at ? (
                <p className="mt-1 text-xs text-gray-500">
                  Last opened: {formatDate(workspace.last_opened_at)}
                </p>
              ) : null}
            </div>

            {workspace?.archived_at ? (
              <div className="flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-2.5">
                <span className="text-xs font-semibold text-amber-800">Archived workspace</span>
                <button
                  type="button"
                  onClick={handleRestore}
                  className="rounded-xl bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700"
                >
                  Restore
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <Features values={values} setValues={setValues} />

      <ResumeUpload onApplyScores={(mapped) => setValues((prev) => ({ ...prev, ...mapped }))} />

      <div className="mx-auto max-w-5xl px-6 mt-4 text-center">
        <button
          type="button"
          onClick={handleWorkspacePredict}
          disabled={predicting}
          className="px-8 py-3.5 bg-black text-white rounded-xl text-lg font-semibold hover:bg-gray-800 disabled:opacity-60"
        >
          {predicting ? "Saving & Predicting..." : "Save & Predict in Workspace"}
        </button>

        {predictError ? (
          <p className="mt-4 text-sm font-medium text-red-600">{predictError}</p>
        ) : null}

        {prediction ? (
          <div className="mt-6 mx-auto max-w-xl rounded-3xl border border-indigo-200 bg-white/90 p-6 text-left shadow-xl backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-indigo-600">
              Latest Prediction · {prediction.model_version}
            </p>
            <p className="mt-2 text-2xl font-bold text-gray-900">{prediction.predicted_role}</p>

            {Array.isArray(prediction.top_3_roles) ? (
              <div className="mt-4 space-y-2">
                {prediction.top_3_roles.map((item) => (
                  <div
                    key={item.role}
                    className="flex items-center justify-between rounded-xl bg-gray-50 px-3.5 py-2 text-sm"
                  >
                    <span className="font-medium text-gray-800">{item.role}</span>
                    <span className="font-semibold text-indigo-600">
                      {(item.probability * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <section className="mx-auto max-w-5xl px-6 mt-12">
        <div className="rounded-3xl border border-gray-200 bg-white/85 p-8 shadow-xl backdrop-blur">
          <h3 className="text-xl font-bold text-gray-900">
            Prediction History ({history.length})
          </h3>

          {history.length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">
              No saved predictions in this workspace yet. Run a prediction above to save it here.
            </p>
          ) : (
            <div className="mt-5 space-y-4">
              {history.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-gray-200 bg-gray-50 p-4"
                >
                  <div>
                    <p className="text-base font-bold text-gray-900">{item.predicted_role}</p>
                    <p className="mt-0.5 text-xs text-gray-500">
                      {formatDate(item.created_at)} · {item.model_version}
                    </p>
                    {Array.isArray(item.top_k) ? (
                      <p className="mt-1.5 text-xs text-gray-600">
                        Top 3:{" "}
                        {item.top_k
                          .map((r) => `${r.role} (${(r.probability * 100).toFixed(1)}%)`)
                          .join(" · ")}
                      </p>
                    ) : null}
                  </div>

                  <button
                    type="button"
                    onClick={() => setValues(valuesArrayToMap(item.values))}
                    className="rounded-xl border border-gray-300 bg-white px-3.5 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100"
                  >
                    Load skills
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
