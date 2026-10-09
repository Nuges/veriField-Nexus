// =============================================================================
// VeriField Nexus — Centralized Date & Time Formatting Utilities
// =============================================================================

/**
 * Safely parses an input string, number, or Date into a Date instance.
 * Ensures ISO-8601 strings without explicit timezone offsets are treated
 * strictly as canonical UTC rather than defaulting to arbitrary client offsets.
 */
export function parseUtcDate(dateInput: string | number | Date | null | undefined): Date | null {
  if (!dateInput) return null;
  if (dateInput instanceof Date) {
    return isNaN(dateInput.getTime()) ? null : dateInput;
  }
  if (typeof dateInput === "number") {
    const d = new Date(dateInput);
    return isNaN(d.getTime()) ? null : d;
  }
  if (typeof dateInput === "string") {
    let clean = dateInput.trim();
    // If ISO date-time string lacks timezone designator ('Z' or [+-]HH:MM), treat as UTC
    if (clean.includes("T") && !clean.endsWith("Z") && !/[+-]\d{2}(:\d{2})?$/.test(clean)) {
      clean += "Z";
    }
    const d = new Date(clean);
    return isNaN(d.getTime()) ? null : d;
  }
  return null;
}

/**
 * Resolves the client user's local timezone via Intl API, or falls back to 'UTC'.
 */
export function getLocalTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

/**
 * Formats a timestamp into a 12-hour or 24-hour time string with optional timezone.
 *
 * @param dateInput - ISO string, timestamp number, or Date object
 * @param timeZone - IANA timezone identifier (e.g., 'Africa/Lagos', 'Asia/Kolkata', or undefined for client local)
 * @param options - Additional Intl.DateTimeFormatOptions
 */
export function formatTime(
  dateInput: string | number | Date | null | undefined,
  timeZone?: string,
  options?: Intl.DateTimeFormatOptions
): string {
  const d = parseUtcDate(dateInput);
  if (!d) return "--:--:--";

  const defaultOptions: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
    ...(timeZone ? { timeZone } : {}),
    ...options,
  };

  try {
    return new Intl.DateTimeFormat([], defaultOptions).format(d);
  } catch {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }
}

/**
 * Formats a timestamp into a readable date string (e.g. "Oct 9, 2026").
 */
export function formatDate(
  dateInput: string | number | Date | null | undefined,
  timeZone?: string,
  options?: Intl.DateTimeFormatOptions
): string {
  const d = parseUtcDate(dateInput);
  if (!d) return "--";

  const defaultOptions: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...(timeZone ? { timeZone } : {}),
    ...options,
  };

  try {
    return new Intl.DateTimeFormat([], defaultOptions).format(d);
  } catch {
    return d.toLocaleDateString();
  }
}

/**
 * Formats a timestamp into a combined date and time string.
 * Example: "Oct 9, 2026, 12:14:04 PM"
 */
export function formatDateTime(
  dateInput: string | number | Date | null | undefined,
  timeZone?: string,
  options?: Intl.DateTimeFormatOptions
): string {
  const d = parseUtcDate(dateInput);
  if (!d) return "--";

  const defaultOptions: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
    ...(timeZone ? { timeZone } : {}),
    ...options,
  };

  try {
    return new Intl.DateTimeFormat([], defaultOptions).format(d);
  } catch {
    return d.toLocaleString();
  }
}

/**
 * Formats time with explicit timezone short name (e.g. "12:14:04 PM WAT" or "04:44:04 PM IST").
 */
export function formatTimeWithZone(
  dateInput: string | number | Date | null | undefined,
  timeZone?: string
): string {
  return formatTime(dateInput, timeZone, { timeZoneName: "short" });
}
