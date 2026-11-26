"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "../components/AuthContext";
import GoogleSignInButton from "../components/GoogleSignInButton";

export default function RegisterPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, register, googleLogin, googleLink } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [pendingGoogleIdToken, setPendingGoogleIdToken] = useState(null);
  const [linkingNotice, setLinkingNotice] = useState("");
  const [linkPassword, setLinkPassword] = useState("");

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/workspaces");
    }
  }, [isAuthenticated, isLoading, router]);

  async function handleRegister(e) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await register(email, password);
      router.push("/workspaces");
    } catch (err) {
      setError(err.message || "Could not create account");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogleCredential(idToken) {
    setError("");
    setSubmitting(true);
    try {
      const outcome = await googleLogin(idToken);
      if (outcome.status === "needs_linking") {
        setPendingGoogleIdToken(idToken);
        setLinkingNotice(outcome.detail);
        setLinkPassword("");
        return;
      }
      router.push("/workspaces");
    } catch (err) {
      setError(err.message || "Google Sign-In failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConfirmLink(e) {
    e.preventDefault();
    if (!pendingGoogleIdToken) return;
    setError("");
    setSubmitting(true);
    try {
      await googleLink(pendingGoogleIdToken, linkPassword);
      setPendingGoogleIdToken(null);
      setLinkPassword("");
      router.push("/workspaces");
    } catch (err) {
      setError(err.message || "Could not verify password to link Google account");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="px-6 py-14">
      <div className="mx-auto max-w-md rounded-3xl border border-gray-200 bg-white/85 p-8 shadow-2xl backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-indigo-600">
          Get Started
        </p>
        <h2 className="mt-2 text-3xl font-bold text-gray-900">
          {pendingGoogleIdToken ? "Verify account ownership" : "Create account"}
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          {pendingGoogleIdToken
            ? "An account already exists with this email. Enter your current password to link Google."
            : "Create a free account to save workspaces and revisit your prediction history."}
        </p>

        {error ? (
          <div
            role="alert"
            className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {error}
          </div>
        ) : null}

        {pendingGoogleIdToken ? (
          <form onSubmit={handleConfirmLink} className="mt-6 space-y-4">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {linkingNotice}
            </div>
            <label className="block text-sm font-semibold text-gray-800">
              Current Password
              <input
                type="password"
                required
                value={linkPassword}
                onChange={(e) => setLinkPassword(e.target.value)}
                placeholder="Enter your existing password"
                className="mt-1.5 w-full rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm focus:border-indigo-600 focus:outline-none"
              />
            </label>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={submitting}
                className="flex-1 rounded-xl bg-black px-5 py-2.5 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-60"
              >
                {submitting ? "Verifying..." : "Verify & Link Google"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setPendingGoogleIdToken(null);
                  setLinkPassword("");
                  setError("");
                }}
                className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <>
            <form onSubmit={handleRegister} className="mt-6 space-y-4">
              <label className="block text-sm font-semibold text-gray-800">
                Email
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="mt-1.5 w-full rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm focus:border-indigo-600 focus:outline-none"
                />
              </label>

              <label className="block text-sm font-semibold text-gray-800">
                Password (min 8 characters)
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="mt-1.5 w-full rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm focus:border-indigo-600 focus:outline-none"
                />
              </label>

              <label className="block text-sm font-semibold text-gray-800">
                Confirm Password
                <input
                  type="password"
                  required
                  minLength={8}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat your password"
                  className="mt-1.5 w-full rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm focus:border-indigo-600 focus:outline-none"
                />
              </label>

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-xl bg-black px-6 py-3 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-60"
              >
                {submitting ? "Creating account..." : "Create account"}
              </button>
            </form>

            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-gray-200" />
              <span className="text-xs uppercase tracking-widest text-gray-400">or</span>
              <div className="h-px flex-1 bg-gray-200" />
            </div>

            <GoogleSignInButton onCredential={handleGoogleCredential} disabled={submitting} />

            <p className="mt-6 text-center text-sm text-gray-600">
              Already have an account?{" "}
              <Link href="/login" className="font-semibold text-indigo-600 hover:underline">
                Sign in
              </Link>
            </p>
          </>
        )}
      </div>
    </main>
  );
}
