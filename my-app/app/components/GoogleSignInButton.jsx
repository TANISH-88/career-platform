"use client";

import { useEffect, useRef, useState } from "react";

const PLACEHOLDER_PREFIX = "your-google-oauth-client-id";

export default function GoogleSignInButton({ onCredential, disabled = false }) {
  const containerRef = useRef(null);
  const callbackRef = useRef(onCredential);
  callbackRef.current = onCredential;

  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
  const isConfigured = Boolean(clientId && !clientId.startsWith(PLACEHOLDER_PREFIX));
  const [scriptError, setScriptError] = useState(false);

  useEffect(() => {
    if (!isConfigured || !containerRef.current) return;

    let cancelled = false;

    function initButton() {
      if (cancelled || !window.google?.accounts?.id || !containerRef.current) {
        return;
      }
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => {
          if (response?.credential) {
            callbackRef.current(response.credential);
          }
        },
      });
      containerRef.current.innerHTML = "";
      window.google.accounts.id.renderButton(containerRef.current, {
        theme: "outline",
        size: "large",
        width: 340,
        text: "continue_with",
      });
    }

    if (window.google?.accounts?.id) {
      initButton();
      return () => {
        cancelled = true;
      };
    }

    const existing = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
    const script = existing || document.createElement("script");
    if (!existing) {
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }

    const onLoad = () => initButton();
    const onError = () => {
      if (!cancelled) setScriptError(true);
    };
    script.addEventListener("load", onLoad);
    script.addEventListener("error", onError);

    return () => {
      cancelled = true;
      script.removeEventListener("load", onLoad);
      script.removeEventListener("error", onError);
    };
  }, [clientId, isConfigured]);

  if (!isConfigured) {
    return (
      <p className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-center text-xs text-gray-500">
        Google Sign-In unavailable in local config (set{" "}
        <code>NEXT_PUBLIC_GOOGLE_CLIENT_ID</code> to enable).
      </p>
    );
  }

  if (scriptError) {
    return (
      <p className="text-center text-xs text-red-600">
        Could not load Google Sign-In script. Use email and password below.
      </p>
    );
  }

  return (
    <div
      className={`flex justify-center ${disabled ? "pointer-events-none opacity-60" : ""}`}
      ref={containerRef}
    />
  );
}
