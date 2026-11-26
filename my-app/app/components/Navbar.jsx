"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "./AuthContext";

export default function Navbar() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  async function handleLogout() {
    await logout();
    router.push("/");
  }

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="w-full py-5 flex flex-wrap justify-between items-center gap-4 px-6 sm:px-10 border-b bg-white/60 backdrop-blur"
    >
      <Link href="/" className="text-2xl font-bold text-gray-900">
        FuturePredict
      </Link>

      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/"
          className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-black"
        >
          Quick Predict
        </Link>

        {isLoading ? (
          <span className="px-3 py-2 text-sm text-gray-400">Checking session...</span>
        ) : isAuthenticated ? (
          <>
            <Link
              href="/workspaces"
              className="px-3 py-2 text-sm font-semibold text-indigo-600 hover:text-indigo-800"
            >
              Workspaces
            </Link>
            <span className="hidden sm:inline text-sm text-gray-600">{user.email}</span>
            <button
              type="button"
              onClick={handleLogout}
              className="px-4 py-2 bg-black text-white rounded-lg text-sm font-medium hover:bg-gray-800"
            >
              Sign out
            </button>
          </>
        ) : (
          <>
            <Link
              href="/login"
              className="px-3 py-2 text-sm font-semibold text-gray-700 hover:text-black"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="px-4 py-2 bg-black text-white rounded-lg text-sm font-medium hover:bg-gray-800"
            >
              Get Started
            </Link>
          </>
        )}
      </div>
    </motion.nav>
  );
}
