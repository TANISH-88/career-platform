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

const REFRESH_LOCK_NAME = "futurepredict_refresh_lock";
const AUTH_CHANNEL_NAME = "futurepredict_auth";

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

function makeTabId() {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return `tab-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/**
 * Create a frontend API client with:
 * - In-memory-only JWT access token (never localStorage/sessionStorage).
 * - Same-origin `/api/*` proxy + `X-Requested-With` CSRF header on cookie endpoints.
 * - Single-flight same-tab refresh + cross-tab coordination via Web Locks (`navigator.locks`)
 *   and `BroadcastChannel` (`TOKEN_REFRESHED`, `LOGOUT`).
 * - Monotonic `sessionEpoch` guard preventing logout-during-refresh from resurrecting auth state.
 * - Delayed 401 guard: if `accessToken` already rotated since the failed request was sent,
 *   retries directly with the newer token without firing a duplicate `/auth/refresh`.
 */
export function createApiClient({
  fetchImpl = (...args) => globalThis.fetch(...args),
  baseUrl = "/api",
  onAuthChange = () => {},
  onSessionExpired = () => {},
  locksImpl = globalThis.navigator?.locks ?? null,
  broadcastChannelFactory = typeof globalThis.BroadcastChannel === "function"
    ? (name) => new globalThis.BroadcastChannel(name)
    : null,
} = {}) {
  const tabId = makeTabId();
  let accessToken = null;
  let currentUser = null;
  let hadAuthenticatedSession = false;
  let inflightRefreshPromise = null;
  let sessionEpoch = 0;

  // Cross-tab in-memory sync state (never persisted to storage)
  let peerRefreshSeq = 0;
  let peerLatestToken = null;

  const channel = broadcastChannelFactory ? broadcastChannelFactory(AUTH_CHANNEL_NAME) : null;
  if (channel) {
    if (typeof channel.unref === "function") {
      channel.unref();
    }
    channel.onmessage = (event) => {
      const msg = event?.data;
      if (!msg || msg.sourceTabId === tabId) return;

      if (msg.type === "TOKEN_REFRESHED" && typeof msg.accessToken === "string") {
        peerRefreshSeq += 1;
        peerLatestToken = msg.accessToken;
        accessToken = msg.accessToken;
        hadAuthenticatedSession = true;
      } else if (msg.type === "LOGOUT") {
        applyLocalClear({ markExpired: false, broadcast: false });
      }
    };
  }

  function postChannel(payload) {
    if (!channel) return;
    try {
      channel.postMessage({ ...payload, sourceTabId: tabId });
    } catch {
      // Ignore closed channel errors during teardown
    }
  }

  function notifyAuth() {
    onAuthChange({
      user: currentUser,
      isAuthenticated: Boolean(accessToken && currentUser),
    });
  }

  function applyLocalClear({ markExpired = false, broadcast = false } = {}) {
    const wasAuthenticated = hadAuthenticatedSession || Boolean(accessToken || currentUser);
    sessionEpoch += 1;
    accessToken = null;
    currentUser = null;
    hadAuthenticatedSession = false;
    peerLatestToken = null;
    notifyAuth();
    if (broadcast) {
      postChannel({ type: "LOGOUT" });
    }
    if (markExpired && wasAuthenticated) {
      onSessionExpired();
    }
  }

  async function withCrossTabLock(fn) {
    if (locksImpl && typeof locksImpl.request === "function") {
      return locksImpl.request(REFRESH_LOCK_NAME, fn);
    }
    return fn();
  }

  function getAccessToken() {
    return accessToken;
  }

  function getUser() {
    return currentUser;
  }

  function close() {
    if (channel && typeof channel.close === "function") {
      channel.close();
    }
  }

  /**
   * Single-flight same-tab + Web-Lock serialized cross-tab refresh.
   * Respects `sessionEpoch` so logout-during-refresh cannot resurrect a dead session.
   */
  async function refreshAccessToken({
    silentIfUnauthenticated = false,
    failedToken = null,
  } = {}) {
    if (inflightRefreshPromise) {
      return inflightRefreshPromise;
    }

    const startEpoch = sessionEpoch;
    const waitStartedSeq = peerRefreshSeq;
    const tokenBeforeRefresh = failedToken ?? accessToken;

    const promise = (async () => {
      try {
        return await withCrossTabLock(async () => {
          // If logout/session reset occurred while waiting, abort immediately.
          if (sessionEpoch !== startEpoch) {
            return null;
          }

          // If another tab already refreshed while we waited for the lock, adopt its token.
          if (
            peerRefreshSeq > waitStartedSeq &&
            peerLatestToken &&
            peerLatestToken !== tokenBeforeRefresh
          ) {
            accessToken = peerLatestToken;
            hadAuthenticatedSession = true;
            return accessToken;
          }

          // If this tab already rotated to a newer token before lock entry, adopt it.
          if (accessToken && tokenBeforeRefresh && accessToken !== tokenBeforeRefresh) {
            return accessToken;
          }

          const res = await fetchImpl(`${baseUrl}/auth/refresh`, {
            method: "POST",
            credentials: "include",
            headers: { ...CSRF_HEADERS },
          });
          const data = await safeParseJson(res);

          // CRITICAL: If user logged out while refresh was in flight, discard response!
          if (sessionEpoch !== startEpoch) {
            return null;
          }

          if (!res.ok || !data?.access_token) {
            applyLocalClear({ markExpired: !silentIfUnauthenticated, broadcast: false });
            return null;
          }

          accessToken = data.access_token;
          hadAuthenticatedSession = true;
          peerLatestToken = data.access_token;
          postChannel({ type: "TOKEN_REFRESHED", accessToken: data.access_token });
          return accessToken;
        });
      } catch {
        if (sessionEpoch === startEpoch) {
          applyLocalClear({ markExpired: !silentIfUnauthenticated, broadcast: false });
        }
        return null;
      } finally {
        if (inflightRefreshPromise === promise) {
          inflightRefreshPromise = null;
        }
      }
    })();

    inflightRefreshPromise = promise;
    return promise;
  }

  async function rawRequest(path, options = {}, { includeAuth = true, retryOn401 = true } = {}) {
    const headers = new Headers(options.headers || {});
    const requestEpoch = sessionEpoch;
    let tokenUsed = null;
    if (includeAuth && accessToken && !headers.has("Authorization")) {
      tokenUsed = accessToken;
      headers.set("Authorization", `Bearer ${tokenUsed}`);
    }

    const res = await fetchImpl(`${baseUrl}${path}`, {
      ...options,
      credentials: "include",
      headers,
    });

    const isNoRefreshPath = NO_AUTO_REFRESH_PATHS.has(path);
    if (res.status === 401 && retryOn401 && includeAuth && !isNoRefreshPath) {
      // If session epoch changed (e.g., user logged out while request was in flight),
      // abort without attempting refresh.
      if (sessionEpoch !== requestEpoch) {
        throw new SessionExpiredError();
      }

      // Delayed 401 guard: another request/tab already rotated accessToken while
      // this slow request was in flight — retry directly with the newer token.
      let nextToken = null;
      if (tokenUsed && accessToken && accessToken !== tokenUsed) {
        nextToken = accessToken;
      } else {
        nextToken = await refreshAccessToken({
          silentIfUnauthenticated: false,
          failedToken: tokenUsed,
        });
      }

      if (!nextToken || sessionEpoch !== requestEpoch) {
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
        applyLocalClear({ markExpired: true, broadcast: false });
        throw new SessionExpiredError(detail);
      }
      throw new ApiError(detail, res.status, detail);
    }

    return data;
  }

  async function loadCurrentUser(expectedEpoch = sessionEpoch) {
    const user = await requestJson("/auth/me", { method: "GET" });
    if (sessionEpoch !== expectedEpoch) {
      return null;
    }
    currentUser = user;
    hadAuthenticatedSession = true;
    notifyAuth();
    return user;
  }

  async function bootstrapSession() {
    const startEpoch = sessionEpoch;
    const token = await refreshAccessToken({ silentIfUnauthenticated: true });
    if (!token || sessionEpoch !== startEpoch) {
      return null;
    }
    try {
      return await loadCurrentUser(startEpoch);
    } catch {
      if (sessionEpoch === startEpoch) {
        applyLocalClear({ markExpired: false, broadcast: false });
      }
      return null;
    }
  }

  async function login(email, password) {
    const startEpoch = sessionEpoch;
    const data = await requestJson(
      "/auth/login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      },
      { includeAuth: false, retryOn401: false }
    );
    if (sessionEpoch !== startEpoch) {
      return null;
    }
    accessToken = data.access_token;
    hadAuthenticatedSession = true;
    peerLatestToken = data.access_token;
    return loadCurrentUser(startEpoch);
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
    const startEpoch = sessionEpoch;
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

    if (sessionEpoch !== startEpoch) {
      return { status: "cancelled", user: null };
    }

    accessToken = data.access_token;
    hadAuthenticatedSession = true;
    peerLatestToken = data.access_token;
    const user = await loadCurrentUser(startEpoch);
    return { status: "authenticated", user };
  }

  async function googleLink(idToken, password) {
    const startEpoch = sessionEpoch;
    const data = await requestJson(
      "/auth/google/link",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: idToken, password }),
      },
      { includeAuth: false, retryOn401: false }
    );
    if (sessionEpoch !== startEpoch) {
      return { status: "cancelled", user: null };
    }
    accessToken = data.access_token;
    hadAuthenticatedSession = true;
    peerLatestToken = data.access_token;
    const user = await loadCurrentUser(startEpoch);
    return { status: "authenticated", user };
  }

  async function logout() {
    // Clear local session state & bump sessionEpoch BEFORE awaiting network so any
    // in-flight refresh cannot resurrect the session.
    applyLocalClear({ markExpired: false, broadcast: true });
    try {
      await rawRequest(
        "/auth/logout",
        {
          method: "POST",
          headers: { ...CSRF_HEADERS },
        },
        { includeAuth: false, retryOn401: false }
      );
    } catch {
      // Logout guarantees local state stays cleared even if server/network errors
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

  // --- Resume Version Management (CP21) ---

  async function listWorkspaceResumeVersions(workspaceId) {
    return requestJson(`/workspaces/${encodeURIComponent(workspaceId)}/resume-versions`, {
      method: "GET",
    });
  }

  async function uploadWorkspaceResumeVersion(workspaceId, file, consent) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("consent", consent ? "true" : "false");
    return requestJson(`/workspaces/${encodeURIComponent(workspaceId)}/resume-versions`, {
      method: "POST",
      body: formData,
    });
  }

  async function deleteWorkspaceResumeVersion(workspaceId, versionId) {
    return requestJson(
      `/workspaces/${encodeURIComponent(workspaceId)}/resume-versions/${encodeURIComponent(versionId)}`,
      { method: "DELETE" }
    );
  }

  async function deleteAllWorkspaceResumeVersions(workspaceId) {
    return requestJson(`/workspaces/${encodeURIComponent(workspaceId)}/resume-versions`, {
      method: "DELETE",
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
    close,
    listWorkspaces,
    createWorkspace,
    getLastActiveWorkspace,
    getWorkspace,
    archiveWorkspace,
    unarchiveWorkspace,
    deleteWorkspace,
    predictInWorkspace,
    getWorkspaceHistory,
    listWorkspaceResumeVersions,
    uploadWorkspaceResumeVersion,
    deleteWorkspaceResumeVersion,
    deleteAllWorkspaceResumeVersions,
    predictAnonymous,
    parseResume,
    requestJson,
  };
}
