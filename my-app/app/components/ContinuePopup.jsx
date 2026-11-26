"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./AuthContext";
import { shouldShowContinuePopup } from "../../lib/continuePopupLogic.mjs";

function formatTimestamp(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ContinuePopup() {
  const pathname = usePathname();
  const router = useRouter();
  const {
    user,
    lastActiveWorkspace,
    continueDismissed,
    dismissContinuePopup,
    sessionExpired,
    dismissSessionExpired,
  } = useAuth();

  if (sessionExpired) {
    return (
      <div
        role="alert"
        className="fixed bottom-6 right-6 z-50 max-w-sm rounded-2xl border border-amber-200 bg-white/95 p-5 shadow-2xl backdrop-blur"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-amber-600">
              Session Expired
            </p>
            <h3 className="mt-1 text-base font-bold text-gray-900">
              Please sign in again
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              Your session expired or was revoked. Anonymous predictions remain available.
            </p>
          </div>
          <button
            type="button"
            onClick={dismissSessionExpired}
            aria-label="Dismiss session expired notice"
            className="rounded-lg px-2 py-1 text-sm text-gray-500 hover:bg-gray-100"
          >
            ✕
          </button>
        </div>
        <div className="mt-4 flex gap-2">
          <Link
            href="/login"
            onClick={dismissSessionExpired}
            className="rounded-xl bg-black px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800"
          >
            Sign in
          </Link>
        </div>
      </div>
    );
  }

  const show = shouldShowContinuePopup({
    user,
    lastActiveWorkspace,
    dismissed: continueDismissed,
    pathname,
  });

  if (!show) {
    return null;
  }

  const stamp = formatTimestamp(
    lastActiveWorkspace.last_opened_at || lastActiveWorkspace.updated_at
  );

  return (
    <div
      role="dialog"
      aria-label="Continue where you left off"
      className="fixed bottom-6 right-6 z-50 w-[360px] max-w-[calc(100vw-2rem)] rounded-3xl border border-gray-200 bg-white/95 p-6 shadow-2xl backdrop-blur"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-indigo-600">
            Welcome back
          </p>
          <h3 className="mt-1 text-lg font-bold text-gray-900">
            Continue where you left off
          </h3>
        </div>
        <button
          type="button"
          onClick={dismissContinuePopup}
          aria-label="Close popup"
          className="rounded-lg px-2 py-1 text-sm text-gray-500 hover:bg-gray-100"
        >
          ✕
        </button>
      </div>

      <div className="mt-3 rounded-2xl border border-gray-100 bg-gray-50 p-3">
        <p className="text-sm font-semibold text-gray-900 truncate">
          {lastActiveWorkspace.name}
        </p>
        {stamp ? (
          <p className="mt-0.5 text-xs text-gray-500">Last opened {stamp}</p>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => {
            dismissContinuePopup();
            router.push(`/workspaces/${lastActiveWorkspace.id}`);
          }}
          className="flex-1 rounded-xl bg-black px-4 py-2.5 text-sm font-semibold text-white hover:bg-gray-800"
        >
          Continue
        </button>
        <Link
          href="/workspaces"
          onClick={dismissContinuePopup}
          className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
        >
          All workspaces
        </Link>
      </div>
    </div>
  );
}
