export const ORDERED_SKILL_KEYS = [
  "computer_architecture",
  "programming_skills",
  "project_management",
  "communication_skills",
  "openness",
  "conscientiousness",
  "extraversion",
  "agreeableness",
  "emotional_range",
  "conversation",
  "openness_change",
  "hedonism",
  "self_enhancement",
  "self_transcendence",
];

/**
 * Map a 14-element numeric array from backend prediction history back into
 * the `{ [key]: string }` map consumed by `<Features />`.
 */
export function valuesArrayToMap(valuesArray) {
  const mapped = {};
  if (!Array.isArray(valuesArray)) return mapped;
  ORDERED_SKILL_KEYS.forEach((key, idx) => {
    if (valuesArray[idx] !== undefined && valuesArray[idx] !== null) {
      mapped[key] = String(valuesArray[idx]);
    }
  });
  return mapped;
}

/**
 * Determine whether the "Continue where you left off?" popup should be shown.
 *
 * Rules:
 * - User must be authenticated.
 * - A non-archived lastActiveWorkspace must exist.
 * - Not dismissed in this browser session.
 * - Do not prompt when already viewing that workspace.
 */
export function shouldShowContinuePopup({
  user,
  lastActiveWorkspace,
  dismissed,
  pathname,
}) {
  if (!user || !lastActiveWorkspace || dismissed) {
    return false;
  }
  if (lastActiveWorkspace.archived_at) {
    return false;
  }
  if (pathname && pathname === `/workspaces/${lastActiveWorkspace.id}`) {
    return false;
  }
  return true;
}
