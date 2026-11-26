export class ApiError extends Error {
  constructor(message, status, detail = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export class SessionExpiredError extends ApiError {
  constructor(message = "Your session has expired. Please sign in again.") {
    super(message, 401, message);
    this.name = "SessionExpiredError";
  }
}

export class NotFoundError extends ApiError {
  constructor(message = "Resource not found", detail = null) {
    super(message, 404, detail);
    this.name = "NotFoundError";
  }
}

const CSRF_HEADERS = {
  "X-Requested-With": "XMLHttpRequest",
};

const NO_AUTO_REFRESH_PATHS = new Set([
  "/auth/login",
  "/auth/register",
  "/auth/google",
  "/auth/google/link",
  "/auth/refresh",
  "/auth/logout",
]);

async function safeParseJson(response) {
  if (response.status === 204) return null;
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/**
 * Create a frontend API client that keeps the JWT access token strictly in
 * memory (closure scope, never localStorage/sessionStorage), proxies through
 * same-origin `/api/*`, sends `X-Requested-With` on cookie endpoints, and
 * deduplicates concurrent refresh requests via a single-flight lock.
 */
export function createApiClient({
  fetchImpl = (...args) => globalThis.fetch(...args),
  baseUrl = "/api",
  onAuthChange = () => {},
  onSessionExpired = () => {},
} = {}) {
  let accessToken = null;
  let currentUser = null;
  let hadAuthenticatedSession = false;
  let inflightRefreshPromise = null;

  function notifyAuth() {
    onAuthChange({
      user: currentUser,
      isAuthenticated: Boolean(accessToken && currentUser),
    });
  }

  function clearSession({ markExpired = false } = {}) {
    const wasAuthenticated = hadAuthenticatedSession || Boolean(accessToken || currentUser);
    accessToken = null;
    currentUser = null;
    hadAuthenticatedSession = false;
    notifyAuth();
    if (markExpired && wasAuthenticated) {
      onSessionExpired();
    }
  }

  function getAccessToken() {
    return accessToken;
  }

  function getUser() {
    return currentUser;
  }

  /**
   * Perform a single-flight `POST /api/auth/refresh`.
   * Multiple concurrent callers share the exact same in-flight promise so only
   * one network request reaches the backend, avoiding false reuse detection
   * against atomic refresh token rotation.
   */
  async function refreshAccessToken({ silentIfUnauthenticated = false } = {}) {
    if (inflightRefreshPromise) {
      return inflightRefreshPromise;
    }

    inflightRefreshPromise = (async () => {
      try {
        const res = await fetchImpl(`${baseUrl}/auth/refresh`, {
          method: "POST",
          credentials: "include",
          headers: {
            ...CSRF_HEADERS,
          },
        });
        const data = await safeParseJson(res);
        if (!res.ok || !data?.access_token) {
          clearSession({ markExpired: !silentIfUnauthenticated });
          return null;
        }
        accessToken = data.access_token;
        hadAuthenticatedSession = true;
        return accessToken;
      } catch {
        clearSession({ markExpired: !silentIfUnauthenticated });
        return null;
      } finally {
        inflightRefreshPromise = null;
      }
    })();

    return inflightRefreshPromise;
  }

  async function rawRequest(path, options = {}, { includeAuth = true, retryOn401 = true } = {}) {
    const headers = new Headers(options.headers || {});
    if (includeAuth && accessToken && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }

    const res = await fetchImpl(`${baseUrl}${path}`, {
      ...options,
      credentials: "include",
      headers,
    });

    const isNoRefreshPath = NO_AUTO_REFRESH_PATHS.has(path);
    if (res.status === 401 && retryOn401 && includeAuth && !isNoRefreshPath) {
      const nextToken = await refreshAccessToken({ silentIfUnauthenticated: false });
      if (!nextToken) {
        throw new SessionExpiredError();
      }
      const retryHeaders = new Headers(options.headers || {});
      retryHeaders.set("Authorization", `Bearer ${nextToken}`);
      return fetchImpl(`${baseUrl}${path}`, {
        ...options,
        credentials: "include",
        headers: retryHeaders,
      });
    }

    return res;
  }

  async function requestJson(path, options = {}, config = {}) {
    const res = await rawRequest(path, options, config);
    const data = await safeParseJson(res);

    if (!res.ok) {
      const detail = data?.detail || `Request failed (${res.status})`;
      if (res.status === 404) {
        throw new NotFoundError(detail, detail);
      }
      if (res.status === 401 && config.includeAuth !== false && !NO_AUTO_REFRESH_PATHS.has(path)) {
        clearSession({ markExpired: true });
        throw new SessionExpiredError(detail);
      }
      throw new ApiError(detail, res.status, detail);
    }

    return data;
  }

  async function loadCurrentUser() {
    const user = await requestJson("/auth/me", { method: "GET" });
    currentUser = user;
    hadAuthenticatedSession = true;
    notifyAuth();
    return user;
  }

  async function bootstrapSession() {
    const token = await refreshAccessToken({ silentIfUnauthenticated: true });
    if (!token) {
      return null;
    }
    try {
      return await loadCurrentUser();
    } catch {
      clearSession({ markExpired: false });
      return null;
    }
  }

  async function login(email, password) {
    const data = await requestJson(
      "/auth/login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      },
      { includeAuth: false, retryOn401: false }
    );
    accessToken = data.access_token;
    hadAuthenticatedSession = true;
    return loadCurrentUser();
  }

  async function register(email, password) {
    await requestJson(
      "/auth/register",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      },
      { includeAuth: false, retryOn401: false }
    );
    return login(email, password);
  }

  async function googleLogin(idToken) {
    const res = await rawRequest(
      "/auth/google",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: idToken }),
      },
      { includeAuth: false, retryOn401: false }
    );
    const data = await safeParseJson(res);

    if (res.status === 409) {
      return {
        status: "needs_linking",
        detail:
          data?.detail ||
          "An account with this email already exists. Enter your password to link Google.",
      };
    }

    if (!res.ok) {
      throw new ApiError(data?.detail || "Google Sign-In failed", res.status, data?.detail);
    }

    accessToken = data.access_token;
    hadAuthenticatedSession = true;
    const user = await loadCurrentUser();
    return { status: "authenticated", user };
  }

  async function googleLink(idToken, password) {
    const data = await requestJson(
      "/auth/google/link",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: idToken, password }),
      },
      { includeAuth: false, retryOn401: false }
    );
    accessToken = data.access_token;
    hadAuthenticatedSession = true;
    const user = await loadCurrentUser();
    return { status: "authenticated", user };
  }

  async function logout() {
    try {
      await rawRequest(
        "/auth/logout",
        {
          method: "POST",
          headers: { ...CSRF_HEADERS },
        },
        { includeAuth: false, retryOn401: false }
      );
    } finally {
      clearSession({ markExpired: false });
    }
  }

  // --- Workspace APIs (authenticated) ---

  async function listWorkspaces({ includeArchived = false } = {}) {
    const query = includeArchived ? "?include_archived=true" : "?include_archived=false";
    return requestJson(`/workspaces${query}`, { method: "GET" });
  }

  async function createWorkspace(name) {
    return requestJson("/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
  }

  async function getLastActiveWorkspace() {
    try {
      return await requestJson("/workspaces/last-active", { method: "GET" });
    } catch (err) {
      if (err instanceof NotFoundError || err?.status === 404) {
        return null;
      }
      throw err;
    }
  }

  async function getWorkspace(workspaceId) {
    return requestJson(`/workspaces/${encodeURIComponent(workspaceId)}`, {
      method: "GET",
    });
  }

  async function archiveWorkspace(workspaceId) {
    return requestJson(`/workspaces/${encodeURIComponent(workspaceId)}/archive`, {
      method: "POST",
    });
  }

  async function unarchiveWorkspace(workspaceId) {
    return requestJson(`/workspaces/${encodeURIComponent(workspaceId)}/unarchive`, {
      method: "POST",
    });
  }

  async function deleteWorkspace(workspaceId) {
    return requestJson(`/workspaces/${encodeURIComponent(workspaceId)}`, {
      method: "DELETE",
    });
  }

  async function predictInWorkspace(workspaceId, values) {
    return requestJson(`/workspaces/${encodeURIComponent(workspaceId)}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values }),
    });
  }

  async function getWorkspaceHistory(workspaceId) {
    return requestJson(`/workspaces/${encodeURIComponent(workspaceId)}/history`, {
      method: "GET",
    });
  }

  // --- Anonymous APIs (never attach Authorization header, never touch workspaces) ---

  async function predictAnonymous(values) {
    return requestJson(
      "/predict",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values }),
      },
      { includeAuth: false, retryOn401: false }
    );
  }

  async function parseResume(file) {
    const formData = new FormData();
    formData.append("file", file);
    return requestJson(
      "/parse-resume",
      {
        method: "POST",
        body: formData,
      },
      { includeAuth: false, retryOn401: false }
    );
  }

  return {
    getAccessToken,
    getUser,
    bootstrapSession,
    refreshAccessToken,
    login,
    register,
    googleLogin,
    googleLink,
    logout,
    listWorkspaces,
    createWorkspace,
    getLastActiveWorkspace,
    getWorkspace,
    archiveWorkspace,
    unarchiveWorkspace,
    deleteWorkspace,
    predictInWorkspace,
    getWorkspaceHistory,
    predictAnonymous,
    parseResume,
    // Expose low-level request helper for tests / custom calls
    requestJson,
  };
}
