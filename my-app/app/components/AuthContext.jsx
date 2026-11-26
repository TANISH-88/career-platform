"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createApiClient } from "../../lib/apiClient.mjs";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [lastActiveWorkspace, setLastActiveWorkspace] = useState(null);
  const [continueDismissed, setContinueDismissed] = useState(false);

  const clientRef = useRef(null);
  if (!clientRef.current) {
    clientRef.current = createApiClient({
      baseUrl: "/api",
      onAuthChange: ({ user: nextUser }) => {
        setUser(nextUser);
        if (nextUser) {
          setSessionExpired(false);
        } else {
          setLastActiveWorkspace(null);
        }
      },
      onSessionExpired: () => {
        setSessionExpired(true);
      },
    });
  }
  const api = clientRef.current;

  const refreshLastActive = useCallback(async () => {
    try {
      const ws = await api.getLastActiveWorkspace();
      setLastActiveWorkspace(ws);
      return ws;
    } catch {
      setLastActiveWorkspace(null);
      return null;
    }
  }, [api]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const restoredUser = await api.bootstrapSession();
        if (!cancelled && restoredUser) {
          await refreshLastActive();
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [api, refreshLastActive]);

  const login = useCallback(
    async (email, password) => {
      setContinueDismissed(false);
      setSessionExpired(false);
      const loggedInUser = await api.login(email, password);
      await refreshLastActive();
      return loggedInUser;
    },
    [api, refreshLastActive]
  );

  const register = useCallback(
    async (email, password) => {
      setContinueDismissed(false);
      setSessionExpired(false);
      const createdUser = await api.register(email, password);
      await refreshLastActive();
      return createdUser;
    },
    [api, refreshLastActive]
  );

  const googleLogin = useCallback(
    async (idToken) => {
      setSessionExpired(false);
      const outcome = await api.googleLogin(idToken);
      if (outcome.status === "authenticated") {
        setContinueDismissed(false);
        await refreshLastActive();
      }
      return outcome;
    },
    [api, refreshLastActive]
  );

  const googleLink = useCallback(
    async (idToken, password) => {
      setContinueDismissed(false);
      setSessionExpired(false);
      const outcome = await api.googleLink(idToken, password);
      if (outcome.status === "authenticated") {
        await refreshLastActive();
      }
      return outcome;
    },
    [api, refreshLastActive]
  );

  const logout = useCallback(async () => {
    setContinueDismissed(true);
    setLastActiveWorkspace(null);
    setSessionExpired(false);
    await api.logout();
  }, [api]);

  const dismissContinuePopup = useCallback(() => {
    setContinueDismissed(true);
  }, []);

  const dismissSessionExpired = useCallback(() => {
    setSessionExpired(false);
  }, []);

  const value = useMemo(
    () => ({
      api,
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      sessionExpired,
      lastActiveWorkspace,
      continueDismissed,
      login,
      register,
      googleLogin,
      googleLink,
      logout,
      refreshLastActive,
      dismissContinuePopup,
      dismissSessionExpired,
    }),
    [
      api,
      user,
      isLoading,
      sessionExpired,
      lastActiveWorkspace,
      continueDismissed,
      login,
      register,
      googleLogin,
      googleLink,
      logout,
      refreshLastActive,
      dismissContinuePopup,
      dismissSessionExpired,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return ctx;
}
