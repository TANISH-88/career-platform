"use client";

import { useState } from "react";
import { ORDERED_SKILL_KEYS, valuesArrayToMap } from "../../lib/continuePopupLogic.mjs";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const MAX_VERSIONS = 10;

const SKILL_LABELS = [
  "Computer Arch.",
  "Programming",
  "Project Mgmt",
  "Communication",
  "Openness",
  "Conscientiousness",
  "Extraversion",
  "Agreeableness",
  "Emotional Range",
  "Conversation",
  "Openness Change",
  "Hedonism",
  "Self-Enhancement",
  "Self-Transcendence",
];

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

export default function WorkspaceResumeVersions({
  workspaceId,
  api,
  versions,
  onVersionsChange,
  onApplyScores,
  onWorkspaceDeleted,
}) {
  const [file, setFile] = useState(null);
  const [consent, setConsent] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [confirmClearAll, setConfirmClearAll] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  const atLimit = versions.length >= MAX_VERSIONS;

  async function handleUpload(e) {
    e.preventDefault();
    setError("");
    setStatus("");

    if (!file) {
      setError("Choose a PDF or DOCX file first.");
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      setError("File exceeds the 5 MB upload limit.");
      return;
    }
    if (!consent) {
      setError("Please check the consent box before uploading your resume for AI scoring.");
      return;
    }
    if (atLimit) {
      setError(`Maximum ${MAX_VERSIONS} resume versions reached. Delete a version first.`);
      return;
    }

    setUploading(true);
    setStatus("Extracting skill scores & running ML prediction...");
    try {
      const created = await api.uploadWorkspaceResumeVersion(workspaceId, file, consent);
      setStatus(
        `Saved Resume Version v${created.version_number}: ${created.predicted_role}`
      );
      setFile(null);
      setExpandedId(created.id);
      if (typeof onApplyScores === "function" && Array.isArray(created.parsed_skills)) {
        onApplyScores(valuesArrayToMap(created.parsed_skills));
      }
      await onVersionsChange();
    } catch (err) {
      if (err?.status === 404 && typeof onWorkspaceDeleted === "function") {
        onWorkspaceDeleted();
        return;
      }
      setStatus("");
      setError(err.message || "Failed to process resume upload.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteVersion(versionId) {
    setError("");
    setStatus("");
    try {
      await api.deleteWorkspaceResumeVersion(workspaceId, versionId);
      await onVersionsChange();
    } catch (err) {
      if (err?.status === 404 && typeof onWorkspaceDeleted === "function") {
        onWorkspaceDeleted();
        return;
      }
      setError(err.message || "Could not delete resume version.");
    }
  }

  async function handleClearAll() {
    setError("");
    setStatus("");
    try {
      await api.deleteAllWorkspaceResumeVersions(workspaceId);
      setConfirmClearAll(false);
      await onVersionsChange();
    } catch (err) {
      if (err?.status === 404 && typeof onWorkspaceDeleted === "function") {
        onWorkspaceDeleted();
        return;
      }
      setError(err.message || "Could not clear resume versions.");
    }
  }

  return (
    <section className="mx-auto max-w-5xl px-6 py-8">
      <div className="rounded-3xl border border-gray-200 bg-white/85 p-8 shadow-2xl backdrop-blur">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-indigo-600">
              Resume Versions
            </p>
            <h3 className="mt-1 text-2xl font-bold text-gray-900">
              Upload Resume &amp; Compare AI + ML Readings
            </h3>
            <p className="mt-1.5 max-w-2xl text-sm text-gray-600">
              Extracts 14 skill scores via Gemini and runs your career prediction model.{" "}
              <span className="font-semibold text-gray-800">
                Raw PDF/DOCX files and personal text are never stored
              </span>{" "}
              — only derived numeric scores and role predictions are saved ({versions.length}/
              {MAX_VERSIONS} versions).
            </p>
          </div>

          {versions.length > 0 ? (
            confirmClearAll ? (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleClearAll}
                  className="rounded-xl bg-red-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-red-700"
                >
                  Confirm clear all
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmClearAll(false)}
                  className="rounded-xl border border-gray-300 px-3 py-2 text-xs text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmClearAll(true)}
                className="rounded-xl border border-red-200 px-3.5 py-2 text-xs font-semibold text-red-600 hover:bg-red-50"
              >
                Delete all resume data
              </button>
            )
          ) : null}
        </div>

        <form onSubmit={handleUpload} className="mt-6 space-y-4">
          <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
            <label className="flex flex-col gap-2 text-sm font-semibold text-gray-800">
              Resume file (PDF or DOCX, max 5 MB)
              <input
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={(event) => {
                  setError("");
                  setFile(event.target.files?.[0] ?? null);
                }}
                className="block w-full rounded-2xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-700 file:mr-4 file:rounded-xl file:border-0 file:bg-black file:px-4 file:py-2 file:text-white hover:border-gray-400"
              />
            </label>

            <button
              type="submit"
              disabled={uploading || !consent || atLimit}
              className="rounded-2xl bg-black px-6 py-3 text-sm font-semibold text-white transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {uploading ? "Analyzing..." : "Save Resume Version"}
            </button>
          </div>

          <label className="flex items-start gap-2.5 rounded-2xl border border-gray-200 bg-gray-50 p-3.5 text-xs text-gray-700">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5 rounded border-gray-300"
            />
            <span>
              I consent to sending extracted text from this file to Gemini AI for one-time skill
              scoring. Neither the uploaded file nor extracted text is retained in the database.
            </span>
          </label>
        </form>

        {error ? (
          <div
            role="alert"
            className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {error}
          </div>
        ) : null}

        {status ? <p className="mt-4 text-sm font-medium text-indigo-700">{status}</p> : null}

        {versions.length > 0 ? (
          <div className="mt-8 space-y-4">
            <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
              Saved Resume Versions ({versions.length})
            </h4>

            {versions.map((ver) => {
              const effectiveExpandedId = expandedId === null ? versions[0]?.id : expandedId;
              const isExpanded = effectiveExpandedId === ver.id;
              return (
                <div
                  key={ver.id}
                  className="rounded-2xl border border-gray-200 bg-gray-50 p-5"
                >
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-indigo-600 px-2.5 py-0.5 text-xs font-bold text-white">
                          v{ver.version_number}
                        </span>
                        <span className="text-lg font-bold text-gray-900">
                          {ver.predicted_role}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-gray-500">
                        {formatDate(ver.created_at)} · ML: {ver.model_version} · LLM:{" "}
                        {ver.parser_model}
                      </p>
                      {Array.isArray(ver.top_k) ? (
                        <p className="mt-1.5 text-xs text-gray-700">
                          Top 3:{" "}
                          {ver.top_k
                            .map((r) => `${r.role} (${(r.probability * 100).toFixed(1)}%)`)
                            .join(" · ")}
                        </p>
                      ) : null}
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedId(isExpanded ? "__none__" : ver.id)
                        }
                        className="rounded-xl border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-100"
                      >
                        {isExpanded ? "Hide LLM scores" : "Show LLM scores"}
                      </button>
                      <button
                        type="button"
                        onClick={() => onApplyScores(valuesArrayToMap(ver.parsed_skills))}
                        className="rounded-xl border border-indigo-200 bg-white px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-50"
                      >
                        Load into inputs
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteVersion(ver.id)}
                        className="rounded-xl border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  {isExpanded && Array.isArray(ver.parsed_skills) ? (
                    <div className="mt-4 grid gap-2 sm:grid-cols-2 md:grid-cols-4 xl:grid-cols-7">
                      {ORDERED_SKILL_KEYS.map((key, idx) => (
                        <div
                          key={key}
                          className="rounded-xl border border-gray-200 bg-white px-2.5 py-2"
                        >
                          <p className="truncate text-[10px] font-semibold uppercase tracking-wider text-gray-500">
                            {SKILL_LABELS[idx] || key}
                          </p>
                          <p className="mt-0.5 text-sm font-bold text-gray-900">
                            {Number(ver.parsed_skills[idx] ?? 0).toFixed(1)}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
    </section>
  );
}
