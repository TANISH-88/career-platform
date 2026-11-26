import assert from "node:assert/strict";
import test from "node:test";
import { createRequire } from "node:module";

import {
  ApiError,
  NotFoundError,
  SessionExpiredError,
  createApiClient,
} from "../lib/apiClient.mjs";
import {
  ORDERED_SKILL_KEYS,
  shouldShowContinuePopup,
  valuesArrayToMap,
} from "../lib/continuePopupLogic.mjs";

const require = createRequire(import.meta.url);

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async text() {
      return body === null || body === undefined ? "" : JSON.stringify(body);
    },
  };
}

test("same-origin Next.js rewrite maps /api/:path* to backend origin", async () => {
  const prev = process.env.BACKEND_URL;
  process.env.BACKEND_URL = "https://api.example.com/";
  delete require.cache[require.resolve("../next.config.js")];
  const nextConfig = require("../next.config.js");
  const rewrites = await nextConfig.rewrites();
  assert.deepEqual(rewrites, [
    {
      source: "/api/:path*",
      destination: "https://api.example.com/:path*",
    },
  ]);
  if (prev === undefined) delete process.env.BACKEND_URL;
  else process.env.BACKEND_URL = prev;
});

test("register, login, and logout keep token strictly in memory and send CSRF header", async () => {
  const calls = [];
  let currentToken = "access-1";

  const mockFetch = async (url, opts = {}) => {
    const headers = new Headers(opts.headers || {});
    calls.push({ url, method: opts.method, credentials: opts.credentials, headers });

    if (url === "/api/auth/register") {
      return jsonResponse(201, { id: "u1", email: "user@example.com", is_active: true });
    }
    if (url === "/api/auth/login") {
      return jsonResponse(200, { access_token: currentToken, token_type: "bearer" });
    }
    if (url === "/api/auth/me") {
      assert.equal(headers.get("authorization"), `Bearer ${currentToken}`);
      return jsonResponse(200, { id: "u1", email: "user@example.com", is_active: true });
    }
    if (url === "/api/auth/logout") {
      assert.equal(headers.get("x-requested-with"), "XMLHttpRequest");
      assert.equal(opts.credentials, "include");
      return jsonResponse(200, { detail: "Logged out" });
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  let lastAuthEvent = null;
  const client = createApiClient({
    fetchImpl: mockFetch,
    onAuthChange: (state) => {
      lastAuthEvent = state;
    },
  });

  const user = await client.register("user@example.com", "strongpassword123");
  assert.equal(user.email, "user@example.com");
  assert.equal(client.getAccessToken(), "access-1");
  assert.equal(lastAuthEvent.isAuthenticated, true);

  await client.logout();
  assert.equal(client.getAccessToken(), null);
  assert.equal(client.getUser(), null);
  assert.equal(lastAuthEvent.isAuthenticated, false);
  assert.equal(calls.some((c) => c.url === "/api/auth/logout"), true);
});

test("Google login handles 409 ownership conflict and completes via /auth/google/link", async () => {
  const calls = [];
  const mockFetch = async (url, opts = {}) => {
    const headers = new Headers(opts.headers || {});
    const body = opts.body ? JSON.parse(opts.body) : null;
    calls.push({ url, body });

    if (url === "/api/auth/google") {
      return jsonResponse(409, {
        detail: "An account with this email already exists. Sign in with your password.",
      });
    }
    if (url === "/api/auth/google/link") {
      if (body.password !== "correct-pw") {
        return jsonResponse(401, { detail: "Invalid password" });
      }
      return jsonResponse(200, { access_token: "google-linked-jwt", token_type: "bearer" });
    }
    if (url === "/api/auth/me") {
      assert.equal(headers.get("authorization"), "Bearer google-linked-jwt");
      return jsonResponse(200, { id: "u1", email: "existing@example.com", is_active: true });
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  const client = createApiClient({ fetchImpl: mockFetch });

  // 1) Google sign-in matching password account returns 409 conflict without logging in
  const conflict = await client.googleLogin("google-id-token-123");
  assert.equal(conflict.status, "needs_linking");
  assert.equal(client.getAccessToken(), null);
  assert.equal(client.getUser(), null);

  // 2) Wrong password fails ownership verification
  await assert.rejects(
    () => client.googleLink("google-id-token-123", "wrong-pw"),
    (err) => err instanceof ApiError && err.status === 401
  );
  assert.equal(client.getAccessToken(), null);

  // 3) Correct password verifies ownership and completes login
  const linked = await client.googleLink("google-id-token-123", "correct-pw");
  assert.equal(linked.status, "authenticated");
  assert.equal(linked.user.email, "existing@example.com");
  assert.equal(client.getAccessToken(), "google-linked-jwt");
  assert.deepEqual(
    calls.map((c) => c.url),
    ["/api/auth/google", "/api/auth/google/link", "/api/auth/google/link", "/api/auth/me"]
  );
});

test("single-flight refresh prevents concurrent /auth/refresh calls on parallel 401s", async () => {
  let refreshCount = 0;
  let activeToken = "expired-token";

  const mockFetch = async (url, opts = {}) => {
    const headers = new Headers(opts.headers || {});
    if (url === "/api/auth/login") {
      return jsonResponse(200, { access_token: "expired-token", token_type: "bearer" });
    }
    if (url === "/api/auth/me") {
      return jsonResponse(200, { id: "u1", email: "race@example.com", is_active: true });
    }
    if (url === "/api/auth/refresh") {
      refreshCount += 1;
      assert.equal(headers.get("x-requested-with"), "XMLHttpRequest");
      assert.equal(opts.credentials, "include");
      // Simulate async network delay while multiple callers hit 401 concurrently
      await new Promise((resolve) => setTimeout(resolve, 25));
      activeToken = "fresh-rotated-token";
      return jsonResponse(200, { access_token: activeToken, token_type: "bearer" });
    }
    if (url.startsWith("/api/workspaces")) {
      if (headers.get("authorization") !== "Bearer fresh-rotated-token") {
        return jsonResponse(401, { detail: "Access token expired" });
      }
      return jsonResponse(200, [{ id: "ws1", name: "Tracked Roles" }]);
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  const client = createApiClient({ fetchImpl: mockFetch });
  await client.login("race@example.com", "strongpassword123");
  assert.equal(client.getAccessToken(), activeToken);

  // Fire 5 concurrent protected requests that all hit 401 simultaneously
  const responses = await Promise.all([
    client.listWorkspaces(),
    client.listWorkspaces(),
    client.listWorkspaces(),
    client.listWorkspaces(),
    client.listWorkspaces(),
  ]);

  assert.equal(refreshCount, 1, "Expected exactly 1 refresh request across 5 concurrent 401s");
  assert.equal(responses.length, 5);
  assert.equal(client.getAccessToken(), "fresh-rotated-token");
});

test("session expiry triggers callback when refresh fails after prior auth, not on anonymous boot", async () => {
  let expiredEvents = 0;
  let refreshShouldFail = true;

  const mockFetch = async (url) => {
    if (url === "/api/auth/refresh") {
      return refreshShouldFail
        ? jsonResponse(401, { detail: "Refresh token expired or revoked" })
        : jsonResponse(200, { access_token: "valid-token", token_type: "bearer" });
    }
    if (url === "/api/auth/login") {
      return jsonResponse(200, { access_token: "initial-token", token_type: "bearer" });
    }
    if (url === "/api/auth/me") {
      return jsonResponse(200, { id: "u1", email: "exp@example.com", is_active: true });
    }
    if (url === "/api/workspaces?include_archived=false") {
      return jsonResponse(401, { detail: "Invalid or expired token" });
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  const client = createApiClient({
    fetchImpl: mockFetch,
    onSessionExpired: () => {
      expiredEvents += 1;
    },
  });

  // 1) Initial unauthenticated bootstrap returns null without triggering session-expired banner
  const bootUser = await client.bootstrapSession();
  assert.equal(bootUser, null);
  assert.equal(expiredEvents, 0);

  // 2) After signing in, a failed refresh on a 401 MUST clear session and trigger onSessionExpired
  await client.login("exp@example.com", "strongpassword123");
  assert.equal(client.getAccessToken(), "initial-token");

  await assert.rejects(
    () => client.listWorkspaces(),
    (err) => err instanceof SessionExpiredError && err.status === 401
  );
  assert.equal(client.getAccessToken(), null);
  assert.equal(client.getUser(), null);
  assert.equal(expiredEvents, 1);
});

test("workspace isolation surfaces 404 NotFoundError and lifecycle + Continue popup logic works", async () => {
  const mockFetch = async (url, opts = {}) => {
    if (url === "/api/auth/login") {
      return jsonResponse(200, { access_token: "tok", token_type: "bearer" });
    }
    if (url === "/api/auth/me") {
      return jsonResponse(200, { id: "user-b", email: "b@example.com", is_active: true });
    }
    if (url === "/api/workspaces/other-user-ws") {
      return jsonResponse(404, { detail: "Workspace not found" });
    }
    if (url === "/api/workspaces/other-user-ws/history") {
      return jsonResponse(404, { detail: "Workspace not found" });
    }
    if (url === "/api/workspaces/other-user-ws/archive") {
      return jsonResponse(404, { detail: "Workspace not found" });
    }
    if (url === "/api/workspaces/ws-own/archive") {
      return jsonResponse(200, { id: "ws-own", name: "Own", archived_at: "2026-11-26T18:00:00Z" });
    }
    if (url === "/api/workspaces/ws-own/unarchive") {
      return jsonResponse(200, { id: "ws-own", name: "Own", archived_at: null });
    }
    if (url === "/api/workspaces/last-active") {
      return jsonResponse(404, { detail: "No active workspaces" });
    }
    if (url === "/api/predict") {
      const headers = new Headers(opts.headers || {});
      assert.equal(headers.has("authorization"), false, "Anonymous /predict must not send Bearer auth");
      return jsonResponse(200, { predicted_role: "Software Developer", top_3_roles: [] });
    }
    throw new Error(`Unexpected URL: ${url} (${opts.method})`);
  };

  const client = createApiClient({ fetchImpl: mockFetch });
  await client.login("b@example.com", "strongpassword123");

  // Accessing another user's workspace or its history/actions throws 404 NotFoundError
  await assert.rejects(
    () => client.getWorkspace("other-user-ws"),
    (err) => err instanceof NotFoundError && err.status === 404
  );
  await assert.rejects(
    () => client.getWorkspaceHistory("other-user-ws"),
    (err) => err instanceof NotFoundError && err.status === 404
  );
  await assert.rejects(
    () => client.archiveWorkspace("other-user-ws"),
    (err) => err instanceof NotFoundError && err.status === 404
  );

  // Own workspace archive + restore work cleanly
  const archived = await client.archiveWorkspace("ws-own");
  assert.ok(archived.archived_at);
  const restored = await client.unarchiveWorkspace("ws-own");
  assert.equal(restored.archived_at, null);

  // last-active 404 maps cleanly to null
  assert.equal(await client.getLastActiveWorkspace(), null);

  // Anonymous prediction stays unauthenticated even when user is logged in
  const anonRes = await client.predictAnonymous(new Array(14).fill(7));
  assert.equal(anonRes.predicted_role, "Software Developer");

  // Continue popup helper rules
  const activeWs = { id: "ws-own", name: "Own", archived_at: null };
  assert.equal(
    shouldShowContinuePopup({
      user: { id: "user-b" },
      lastActiveWorkspace: activeWs,
      dismissed: false,
      pathname: "/",
    }),
    true
  );
  assert.equal(
    shouldShowContinuePopup({
      user: { id: "user-b" },
      lastActiveWorkspace: activeWs,
      dismissed: false,
      pathname: "/workspaces/ws-own",
    }),
    false
  );
  assert.equal(
    shouldShowContinuePopup({
      user: { id: "user-b" },
      lastActiveWorkspace: { ...activeWs, archived_at: "2026-11-26T00:00:00Z" },
      dismissed: false,
      pathname: "/",
    }),
    false
  );

  // History array -> skill form map aligns with 14 orderedKeys
  const sampleValues = Array.from({ length: 14 }, (_, idx) => (idx % 10) + 1);
  const mapped = valuesArrayToMap(sampleValues);
  assert.equal(Object.keys(mapped).length, 14);
  assert.equal(mapped[ORDERED_SKILL_KEYS[0]], "1");
  assert.equal(mapped[ORDERED_SKILL_KEYS[13]], "4");
});

test("concurrent browser tabs serialize refresh via Web Lock + BroadcastChannel and sync logout", async () => {
  // In-memory BroadcastChannel + exclusive Web Lock bus simulating 2 open browser tabs
  const channels = new Set();
  const broadcastChannelFactory = () => {
    const ch = {
      onmessage: null,
      postMessage(data) {
        for (const peer of channels) {
          if (peer !== ch && typeof peer.onmessage === "function") {
            peer.onmessage({ data });
          }
        }
      },
      close() {
        channels.delete(ch);
      },
    };
    channels.add(ch);
    return ch;
  };

  let lockTail = Promise.resolve();
  const locksImpl = {
    request(_name, fn) {
      const next = lockTail.then(() => fn());
      lockTail = next.catch(() => {});
      return next;
    },
  };

  let refreshCount = 0;
  let logoutCount = 0;
  const mockFetch = async (url, opts = {}) => {
    const headers = new Headers(opts.headers || {});
    if (url === "/api/auth/refresh") {
      refreshCount += 1;
      await new Promise((r) => setTimeout(r, 20));
      return jsonResponse(200, { access_token: "tab-shared-token", token_type: "bearer" });
    }
    if (url === "/api/auth/me") {
      assert.equal(headers.get("authorization"), "Bearer tab-shared-token");
      return jsonResponse(200, { id: "u1", email: "tabs@example.com", is_active: true });
    }
    if (url === "/api/auth/logout") {
      logoutCount += 1;
      return jsonResponse(200, { detail: "Logged out" });
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  let tabBLoggedOut = false;
  const tabA = createApiClient({ fetchImpl: mockFetch, locksImpl, broadcastChannelFactory });
  const tabB = createApiClient({
    fetchImpl: mockFetch,
    locksImpl,
    broadcastChannelFactory,
    onAuthChange: (state) => {
      if (!state.isAuthenticated) tabBLoggedOut = true;
    },
  });

  const [userA, userB] = await Promise.all([tabA.bootstrapSession(), tabB.bootstrapSession()]);
  assert.equal(refreshCount, 1, "Cross-tab Web Lock + BroadcastChannel must issue strictly 1 refresh");
  assert.equal(userA.email, "tabs@example.com");
  assert.equal(userB.email, "tabs@example.com");
  assert.equal(tabA.getAccessToken(), "tab-shared-token");
  assert.equal(tabB.getAccessToken(), "tab-shared-token");

  await tabA.logout();
  assert.equal(logoutCount, 1);
  assert.equal(tabA.getAccessToken(), null);
  assert.equal(tabB.getAccessToken(), null);
  assert.equal(tabB.getUser(), null);
  assert.equal(tabBLoggedOut, true);

  tabA.close();
  tabB.close();
});

test("delayed 401 response reuses newer rotated token without issuing a duplicate refresh", async () => {
  let refreshCount = 0;
  let releaseSlow401;
  const slow401Gate = new Promise((r) => {
    releaseSlow401 = r;
  });
  let slowFirstAttemptDone = false;

  const mockFetch = async (url, opts = {}) => {
    const headers = new Headers(opts.headers || {});
    if (url === "/api/auth/login") {
      return jsonResponse(200, { access_token: "token-v1", token_type: "bearer" });
    }
    if (url === "/api/auth/me") {
      return jsonResponse(200, { id: "u1", email: "delay@example.com", is_active: true });
    }
    if (url === "/api/auth/refresh") {
      refreshCount += 1;
      return jsonResponse(200, { access_token: "token-v2", token_type: "bearer" });
    }
    if (url === "/api/workspaces/slow") {
      if (!slowFirstAttemptDone && headers.get("authorization") === "Bearer token-v1") {
        slowFirstAttemptDone = true;
        await slow401Gate;
        return jsonResponse(401, { detail: "Token v1 expired" });
      }
      assert.equal(headers.get("authorization"), "Bearer token-v2");
      return jsonResponse(200, { id: "slow", name: "Recovered Without Extra Refresh" });
    }
    if (url === "/api/workspaces/fast") {
      if (headers.get("authorization") === "Bearer token-v1") {
        return jsonResponse(401, { detail: "Token v1 expired" });
      }
      assert.equal(headers.get("authorization"), "Bearer token-v2");
      return jsonResponse(200, { id: "fast", name: "Triggered Refresh" });
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  const client = createApiClient({ fetchImpl: mockFetch });
  await client.login("delay@example.com", "strongpassword123");

  // Start slow request using token-v1, then let fast request trigger refresh to token-v2
  const slowPromise = client.getWorkspace("slow");
  const fastResult = await client.getWorkspace("fast");
  assert.equal(fastResult.id, "fast");
  assert.equal(refreshCount, 1);

  // Now release the delayed 401 for the earlier slow request
  releaseSlow401();
  const slowResult = await slowPromise;
  assert.equal(slowResult.id, "slow");
  assert.equal(refreshCount, 1, "Delayed 401 must NOT trigger a second /auth/refresh");
});

test("logout during in-flight refresh prevents stale refresh response from resurrecting session", async () => {
  let resolveRefreshFetch;
  const pendingRefresh = new Promise((r) => {
    resolveRefreshFetch = r;
  });

  const mockFetch = async (url) => {
    if (url === "/api/auth/login") {
      return jsonResponse(200, { access_token: "tok-1", token_type: "bearer" });
    }
    if (url === "/api/auth/me") {
      return jsonResponse(200, { id: "u1", email: "race@example.com", is_active: true });
    }
    if (url === "/api/auth/refresh") {
      return pendingRefresh;
    }
    if (url === "/api/auth/logout") {
      return jsonResponse(200, { detail: "Logged out" });
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  let authState = null;
  const client = createApiClient({
    fetchImpl: mockFetch,
    onAuthChange: (s) => {
      authState = s;
    },
  });

  await client.login("race@example.com", "strongpassword123");
  const inflightRefresh = client.refreshAccessToken();

  // User clicks Sign out while /auth/refresh is still pending over the network
  await client.logout();
  assert.equal(client.getAccessToken(), null);
  assert.equal(authState.isAuthenticated, false);

  // Stale refresh response now arrives with 200 — MUST be discarded
  resolveRefreshFetch(jsonResponse(200, { access_token: "resurrected-stale-token", token_type: "bearer" }));
  const refreshOutcome = await inflightRefresh;
  assert.equal(refreshOutcome, null);
  assert.equal(client.getAccessToken(), null);
  assert.equal(client.getUser(), null);
  assert.equal(authState.isAuthenticated, false);
});

test("CP21 workspace resume versions client enforces consent, lists, deletes, and surfaces 404 isolation", async () => {
  const mockFetch = async (url, opts = {}) => {
    if (url === "/api/auth/login") {
      return jsonResponse(200, { access_token: "tok-cp21", token_type: "bearer" });
    }
    if (url === "/api/auth/me") {
      return jsonResponse(200, { id: "u1", email: "cp21@example.com", is_active: true });
    }
    if (url === "/api/workspaces/ws-1/resume-versions" && opts.method === "POST") {
      const consent = opts.body?.get("consent");
      if (consent !== "true") {
        return jsonResponse(422, { detail: "Explicit consent is required" });
      }
      return jsonResponse(201, {
        id: "rv-1",
        workspace_id: "ws-1",
        version_number: 1,
        parsed_skills: new Array(14).fill(7),
        predicted_role: "Software Developer",
        top_k: [],
        model_version: "frf_v1",
        parser_model: "gemini-2.5-flash-lite",
        created_at: "2026-11-26T18:30:00Z",
      });
    }
    if (url === "/api/workspaces/ws-1/resume-versions" && opts.method === "GET") {
      return jsonResponse(200, [{ id: "rv-1", version_number: 1 }]);
    }
    if (url === "/api/workspaces/ws-1/resume-versions/rv-1" && opts.method === "DELETE") {
      return jsonResponse(204, null);
    }
    if (url === "/api/workspaces/other-ws/resume-versions") {
      return jsonResponse(404, { detail: "Workspace not found" });
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  const client = createApiClient({ fetchImpl: mockFetch });
  await client.login("cp21@example.com", "strongpassword123");

  const fakeFile = new Blob(["%PDF-1.4"], { type: "application/pdf" });
  await assert.rejects(
    () => client.uploadWorkspaceResumeVersion("ws-1", fakeFile, false),
    (err) => err instanceof ApiError && err.status === 422
  );

  const created = await client.uploadWorkspaceResumeVersion("ws-1", fakeFile, true);
  assert.equal(created.version_number, 1);
  assert.equal(created.predicted_role, "Software Developer");

  const listed = await client.listWorkspaceResumeVersions("ws-1");
  assert.equal(listed.length, 1);

  await client.deleteWorkspaceResumeVersion("ws-1", "rv-1");

  await assert.rejects(
    () => client.listWorkspaceResumeVersions("other-ws"),
    (err) => err instanceof NotFoundError && err.status === 404
  );
});
