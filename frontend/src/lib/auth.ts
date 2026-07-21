export function setAuthStatusCookie(maxAgeSeconds = 60 * 60 * 24 * 30) {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `auth_status=1; path=/; max-age=${maxAgeSeconds}`;
}

export function clearAuthStatusCookie() {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = "auth_status=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
}
