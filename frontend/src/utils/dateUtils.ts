/**
 * Utility functions for date formatting and manipulation.
 */

/**
 * Formats a date string to a localized string representation with optional formatting options and fallback value.
 * @param dateString - ISO 8601 date string or any valid date string.
 * @param options - Optional formatting options for toLocaleString.
 * @param fallback - Optional fallback value if the date is invalid.
 * @returns Formatted date string or fallback value.
 */
export const formatDate = (
  dateString: string,
  options?: Intl.DateTimeFormatOptions,
  fallback = 'N/A'
): string => {
  if (!dateString) return fallback;

  const date = new Date(dateString);
  if (isNaN(date.getTime())) return fallback;

  return date.toLocaleString(undefined, options);
};
