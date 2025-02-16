/**
 * Converts a snake_case string to camelCase
 * @param str The snake_case string to convert
 * @returns The camelCase version of the string
 */
export const snakeToCamel = (str: string): string => {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
};

/**
 * Recursively converts all snake_case keys in an object to camelCase
 * @param obj The object containing snake_case keys
 * @returns A new object with all keys converted to camelCase
 */
export const convertKeysToCamel = <T>(obj: T): T => {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }

  // Handle Date objects
  if (obj instanceof Date) {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => convertKeysToCamel(item)) as T;
  }

  const newObj: Record<string, unknown> = {};

  Object.keys(obj as object).forEach((key) => {
    const value = (obj as Record<string, unknown>)[key];
    const newKey = snakeToCamel(key);

    // Recursively convert nested objects, preserving Date objects
    newObj[newKey] = value && typeof value === 'object'
      ? (value instanceof Date ? value : convertKeysToCamel(value))
      : value;
  });

  return newObj as T;
};
