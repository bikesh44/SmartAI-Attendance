import assert from "node:assert/strict";
import { formatLastLogin, formatDate, formatActivityTime } from "./dateUtils.js";

console.log("Running dateUtils tests...");

// Test 1: User who has never logged in displays "Never"
assert.equal(formatLastLogin(null), "Never", "null timestamp must return Never");
assert.equal(formatLastLogin(undefined), "Never", "undefined timestamp must return Never");
assert.equal(formatLastLogin(""), "Never", "empty string timestamp must return Never");

// Test 2: Invalid timestamps display "Unavailable" and never produce fabricated time
assert.equal(formatLastLogin("not-a-valid-date"), "Unavailable", "invalid string must return Unavailable");
assert.equal(formatLastLogin("2026-99-99T99:99:99Z"), "Unavailable", "malformed ISO must return Unavailable");
assert.equal(formatLastLogin(NaN), "Unavailable", "NaN must return Unavailable");

// Test 3: Timestamps occurring today display "Today, <time>" in Asia/Kolkata
{
  const now = new Date();
  const todayIso = now.toISOString();
  const result = formatLastLogin(todayIso);
  assert.match(
    result,
    /^Today, \d{1,2}:\d{2}\s?(AM|PM)$/,
    `Expected Today format, got: ${result}`
  );
}

// Test 4: Historical timestamps on another date display "MMM D, YYYY, h:mm A"
{
  // 2026-10-19T08:44:43Z is 14:14:43 in Asia/Kolkata (2:14 PM)
  const resultUtc = formatLastLogin("2026-10-19T08:44:43Z");
  assert.equal(
    resultUtc,
    "Oct 19, 2026, 2:14 PM",
    `Expected 'Oct 19, 2026, 2:14 PM', got: ${resultUtc}`
  );
}

// Test 5: Timestamps with explicit offset (+05:30) are parsed correctly
{
  const resultOffset = formatLastLogin("2026-10-19T14:14:43+05:30");
  assert.equal(
    resultOffset,
    "Oct 19, 2026, 2:14 PM",
    `Expected 'Oct 19, 2026, 2:14 PM', got: ${resultOffset}`
  );
}

// Test 6: Timestamps with negative offset (-04:00) are converted correctly to Asia/Kolkata
{
  // 2026-10-19T04:44:43-04:00 is 08:44:43 UTC -> 14:14:43 Asia/Kolkata (2:14 PM)
  const resultNegOffset = formatLastLogin("2026-10-19T04:44:43-04:00");
  assert.equal(
    resultNegOffset,
    "Oct 19, 2026, 2:14 PM",
    `Expected 'Oct 19, 2026, 2:14 PM', got: ${resultNegOffset}`
  );
}

// Test 7: formatDate utility standard format
assert.equal(formatDate(null), "—");
assert.equal(formatDate("2026-10-19T08:44:43Z"), "Oct 19, 2026");

// Test 8: formatActivityTime utility
assert.equal(formatActivityTime(null), "—");
assert.equal(formatActivityTime(undefined), "—");
assert.equal(formatActivityTime("invalid"), "Unavailable");
assert.equal(formatActivityTime(new Date(Date.now() - 10000)), "Just now");
assert.equal(formatActivityTime(new Date(Date.now() - 5 * 60 * 1000)), "5m ago");
assert.equal(formatActivityTime("2026-10-19T08:44:43Z"), "Oct 19, 2026, 2:14 PM");

console.log("All dateUtils tests passed successfully!");
