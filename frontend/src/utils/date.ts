/**
 * Safely formats a date string to a localized string representation
 * @param dateString - ISO 8601 date string or any valid date string
 * @param fallback - Optional fallback value if date is invalid
 * @returns Formatted date string or fallback value
 */
export const formatDate = (dateString: string, fallback = 'N/A'): string => {
  if (!dateString) return fallback;

  const date = new Date(dateString);
  if (isNaN(date.getTime())) return fallback;

  return date.toLocaleString();
};
