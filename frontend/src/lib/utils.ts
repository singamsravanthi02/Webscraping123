import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error) {
    return error.message || fallback;
  }

  return fallback;
}

export function asArray<T>(value: unknown): T[] {
  if (Array.isArray(value)) {
    return value as T[];
  }

  if (value && typeof value === "object") {
    const items = (value as { value?: unknown }).value;
    if (Array.isArray(items)) {
      return items as T[];
    }
  }

  return [];
}

export function hasValidExternalUrl(value?: string | null) {
  if (!value) {
    return false;
  }

  if (value.startsWith("#") || value.startsWith("javascript:")) {
    return false;
  }

  try {
    const url = new URL(value);
    return !url.hostname.endsWith("example.com") && url.hostname !== "localhost" && url.hostname !== "127.0.0.1";
  } catch {
    return false;
  }
}
