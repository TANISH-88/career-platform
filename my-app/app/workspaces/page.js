"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../components/AuthContext";

function formatDate(iso) {
  if (!iso) return "Never";
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

export default function WorkspacesPage() {
  const router = useRouter();
  const { api, isAuthenticated, isLoading, refreshLastActive } = useAuth();

  const [workspaces, setWorkspaces] = useState([]);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  const loadWorkspaces = useCallback(async () => {
    setFetching(true);
    setError("");
    try {
      const list = await api.listWorkspaces({ includeArchived });
      setWorkspaces(list);
    } catch (err) {
      setError(err.message || "Failed to load workspaces");
    } finally {
      setFetching(false);
    }
  }, [api, includeArchived]);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      loadWorkspaces();
    }
  }, [isAuthenticated, isLoading, loadWorkspaces]);

  async function handleCreate(e) {
    e.preventDefault();
    const trimmed = newName.trim();
    if (!trimmed) return;
    setBusy(true);
    setError("");
    try {
      const created = await api.createWorkspace(trimmed);
      setNewName("");
      await refreshLastActive();
      router.push(`/workspaces/${created.id}`);
    } catch (err) {
      setError(err.message || "Failed to create workspace");
    } finally {
      setBusy(false);
    }
  }

  async function handleArchive(id) {
    setError("");
    try {
      await api.archiveWorkspace(id);
      await Promise.all([loadWorkspaces(), refreshLastActive()]);
    } catch (err) {
      setError(err.message || "Could not archive workspace");
    }
  }

  async function handleRestore(id) {
    setError("");
    try {
      await api.unarchiveWorkspace(id);
      await Promise.all([loadWorkspaces(), refreshLastActive()]);
    } catch (err) {
      setError(err.message || "Could not restore workspace");
    }
  }

  async function handleDelete(id) {
    setError("");
    try {
      await api.deleteWorkspace(id);
      setConfirmDeleteId(null);
      await Promise.all([loadWorkspaces(), refreshLastActive()]);
    } catch (err) {
      setError(err.message || "Could not delete workspace");
    }
  }

  if (isLoading) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-16 text-center text-gray-600">
        Loading your session...
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="px-6 py-16">
        <div className="mx-auto max-w-lg rounded-3xl border border-gray-200 bg-white/85 p-8 text-center shadow-2xl backdrop-blur">
          <h2 className="text-2xl font-bold text-gray-900">Sign in to view workspaces</h2>
          <p className="mt-2 text-sm text-gray-600">
            Save skill profiles and track role predictions across sessions, or keep using{" "}
            <Link href="/" className="font-semibold text-indigo-600 hover:underline">
              anonymous quick predict
            </Link>
            .
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link
              href="/login"
              className="rounded-xl bg-black px-5 py-2.5 text-sm font-semibold text-white hover:bg-gray-800"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="rounded-xl border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              Create account
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const activeList = workspaces.filter((w) => !w.archived_at);
  const archivedList = workspaces.filter((w) => Boolean(w.archived_at));

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="rounded-3xl border border-gray-200 bg-white/85 p-8 shadow-2xl backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-indigo-600">
              Workspaces
            </p>
            <h2 className="mt-1 text-3xl font-bold text-gray-900">Your career tracks</h2>
          </div>

          <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3.5 py-2 text-sm font-medium text-gray-700">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
              className="rounded border-gray-300"
            />
            Show archived
          </label>
        </div>

        <form onSubmit={handleCreate} className="mt-6 flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            required
            maxLength={120}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="New workspace name (e.g. Backend Roles 2026)"
            className="flex-1 rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm focus:border-indigo-600 focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy || !newName.trim()}
            className="rounded-2xl bg-black px-6 py-3 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-60"
          >
            {busy ? "Creating..." : "Create workspace"}
          </button>
        </form>

        {error ? (
          <div
            role="alert"
            className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {error}
          </div>
        ) : null}

        <section className="mt-8">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
            Active workspaces ({activeList.length})
          </h3>

          {fetching && workspaces.length === 0 ? (
            <p className="mt-4 text-sm text-gray-500">Loading workspaces...</p>
          ) : activeList.length === 0 ? (
            <p className="mt-4 rounded-2xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-sm text-gray-500">
              No active workspaces yet. Create one above to save your skill scores and predictions.
            </p>
          ) : (
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {activeList.map((ws) => (
                <div
                  key={ws.id}
                  className="flex flex-col justify-between rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition hover:shadow-md"
                >
                  <div>
                    <h4 className="text-lg font-bold text-gray-900">{ws.name}</h4>
                    <p className="mt-1 text-xs text-gray-500">
                      Last opened: {formatDate(ws.last_opened_at || ws.created_at)}
                    </p>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-2">
                    <Link
                      href={`/workspaces/${ws.id}`}
                      className="rounded-xl bg-black px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800"
                    >
                      Continue
                    </Link>
                    <button
                      type="button"
                      onClick={() => handleArchive(ws.id)}
                      className="rounded-xl border border-gray-300 px-3.5 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
                    >
                      Archive
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {includeArchived ? (
          <section className="mt-10 border-t pt-8">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
              Archived workspaces ({archivedList.length})
            </h3>

            {archivedList.length === 0 ? (
              <p className="mt-3 text-sm text-gray-500">No archived workspaces.</p>
            ) : (
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                {archivedList.map((ws) => (
                  <div
                    key={ws.id}
                    className="flex flex-col justify-between rounded-2xl border border-gray-200 bg-gray-50 p-5"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-lg font-bold text-gray-700">{ws.name}</h4>
                        <span className="rounded-full bg-gray-200 px-2.5 py-0.5 text-xs font-semibold text-gray-600">
                          Archived
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-gray-500">
                        Archived on: {formatDate(ws.archived_at)}
                      </p>
                    </div>

                    <div className="mt-5 flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleRestore(ws.id)}
                        className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
                      >
                        Restore
                      </button>

                      {confirmDeleteId === ws.id ? (
                        <>
                          <button
                            type="button"
                            onClick={() => handleDelete(ws.id)}
                            className="rounded-xl bg-red-600 px-3.5 py-2 text-sm font-semibold text-white hover:bg-red-700"
                          >
                            Confirm delete
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmDeleteId(null)}
                            className="rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-white"
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setConfirmDeleteId(ws.id)}
                          className="rounded-xl border border-red-200 px-3.5 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        ) : null}
      </div>
    </main>
  );
}
