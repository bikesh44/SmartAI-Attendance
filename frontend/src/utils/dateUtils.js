/**
 * Shared date and time formatting utilities.
 */

export const DEFAULT_DISPLAY_TIMEZONE = "Asia/Kolkata";

/**
 * Formats a Last Login timestamp into a human-readable string:
 * - If missing/null/empty: "Never"
 * - If invalid date: "Unavailable"
 * - If login was today in display timezone: "Today, 3:33 PM"
 * - If login was on another date in display timezone: "Oct 19, 2026, 2:14 PM"
 *
 * @param {string|Date|null|undefined} dateInput - ISO string or Date object
 * @param {string} [timeZone=DEFAULT_DISPLAY_TIMEZONE] - IANA timezone identifier
 * @returns {string} Formatted string
 */
export function formatLastLogin(dateInput, timeZone = DEFAULT_DISPLAY_TIMEZONE) {
  if (dateInput === null || dateInput === undefined || dateInput === "") {
    return "Never";
  }

  if (typeof dateInput === "number" && isNaN(dateInput)) {
    console.warn("Invalid last_login timestamp received:", dateInput);
    return "Unavailable";
  }

  try {
    const date = dateInput instanceof Date ? dateInput : new Date(dateInput);

    if (isNaN(date.getTime())) {
      console.warn("Invalid last_login timestamp received:", dateInput);
      return "Unavailable";
    }

    const getDateKey = (d) => {
      return new Intl.DateTimeFormat("en-CA", {
        timeZone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(d);
    };

    const isToday = getDateKey(date) === getDateKey(new Date());

    const timeStr = date.toLocaleTimeString("en-US", {
      timeZone,
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });

    if (isToday) {
      return `Today, ${timeStr}`;
    }

    const dateStr = date.toLocaleDateString("en-US", {
      timeZone,
      month: "short",
      day: "numeric",
      year: "numeric",
    });

    return `${dateStr}, ${timeStr}`;
  } catch (err) {
    console.error("Error formatting last_login timestamp:", err);
    return "Unavailable";
  }
}

/**
 * Standard date formatter for calendar dates (e.g. "Oct 19, 2026").
 *
 * @param {string|Date|null|undefined} dateInput
 * @param {string} [timeZone=DEFAULT_DISPLAY_TIMEZONE]
 * @returns {string}
 */
export function formatDate(dateInput, timeZone = DEFAULT_DISPLAY_TIMEZONE) {
  if (!dateInput) return "—";

  try {
    const date = dateInput instanceof Date ? dateInput : new Date(dateInput);
    if (isNaN(date.getTime())) return "—";

    return date.toLocaleDateString("en-US", {
      timeZone,
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return String(dateInput);
  }
}

/**
 * Activity feed time formatter:
 * - "Just now" (< 1 min)
 * - "Xm ago" (< 60 min)
 * - "Xh ago" (< 12 hours)
 * - Falls back to formatLastLogin ("Today, 3:33 PM" or "Oct 19, 2026, 2:14 PM")
 *
 * @param {string|Date|null|undefined} dateInput
 * @param {string} [timeZone=DEFAULT_DISPLAY_TIMEZONE]
 * @returns {string}
 */
export function formatActivityTime(dateInput, timeZone = DEFAULT_DISPLAY_TIMEZONE) {
  if (dateInput === null || dateInput === undefined || dateInput === "") {
    return "—";
  }

  if (typeof dateInput === "number" && isNaN(dateInput)) {
    return "Unavailable";
  }

  try {
    const date = dateInput instanceof Date ? dateInput : new Date(dateInput);
    if (isNaN(date.getTime())) return "Unavailable";

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins >= 0 && diffMins < 1) return "Just now";
    if (diffMins >= 1 && diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours >= 1 && diffHours < 12) return `${diffHours}h ago`;

    return formatLastLogin(date, timeZone);
  } catch {
    return "Unavailable";
  }
}
