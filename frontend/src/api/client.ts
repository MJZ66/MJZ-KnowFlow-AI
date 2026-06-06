/**
 * HTTP client — JWT in HttpOnly cookies + CSRF double-submit protection.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
const CSRF_HEADER = 'X-CSRF-Token';
const CSRF_COOKIE = 'kf_csrf';

interface ApiErrorPayload {
  code?: string;
  message?: string;
  message_en?: string;
  detail?: string;
}

const FETCH_CREDENTIALS: RequestCredentials = 'include';
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

let csrfToken: string | null = null;
let csrfPromise: Promise<string> | null = null;

function formatApiErrorBody(data: ApiErrorPayload & { detail?: unknown }): string {
  if (data.message || data.message_en) {
    return JSON.stringify({
      code: data.code,
      message: data.message,
      message_en: data.message_en,
    });
  }
  if (typeof data.detail === 'string') return data.detail;
  return `Request failed`;
}

function readCsrfCookie(): string | null {
  const prefix = `${CSRF_COOKIE}=`;
  for (const part of document.cookie.split(';')) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.slice(prefix.length));
    }
  }
  return null;
}

/** Bootstrap or refresh CSRF token (required before any mutating request). */
export async function ensureCsrfToken(force = false): Promise<string> {
  if (!force && csrfToken) return csrfToken;

  const fromCookie = readCsrfCookie();
  if (!force && fromCookie) {
    csrfToken = fromCookie;
    return csrfToken;
  }

  if (csrfPromise) return csrfPromise;

  csrfPromise = (async () => {
    const res = await fetch(`${API_BASE}/api/auth/csrf`, {
      credentials: FETCH_CREDENTIALS,
    });
    if (!res.ok) {
      throw new Error('Failed to obtain CSRF token');
    }
    const data = (await res.json()) as { csrf_token: string };
    csrfToken = data.csrf_token || readCsrfCookie();
    if (!csrfToken) {
      throw new Error('CSRF token missing from response');
    }
    return csrfToken;
  })();

  try {
    return await csrfPromise;
  } finally {
    csrfPromise = null;
  }
}

export function resetCsrfToken() {
  csrfToken = null;
}

/** Remove legacy localStorage tokens from pre-cookie auth. */
export function clearLegacyTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

/** @deprecated No-op — tokens live in HttpOnly cookies. */
export function setTokens(_access: string, _refresh: string) {
  clearLegacyTokens();
}

/** @deprecated Clears server session via logout; kept for compatibility. */
export function clearTokens() {
  clearLegacyTokens();
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const token = await ensureCsrfToken();
      const res = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: 'POST',
        credentials: FETCH_CREDENTIALS,
        headers: {
          'Content-Type': 'application/json',
          [CSRF_HEADER]: token,
        },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        await ensureCsrfToken(true);
      }
      return res.ok;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function buildHeaders(
  options: RequestInit,
  existing: Record<string, string>,
): Promise<Record<string, string>> {
  const headers: Record<string, string> = { ...existing };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] ?? 'application/json';
  }

  const method = (options.method ?? 'GET').toUpperCase();
  if (MUTATING_METHODS.has(method)) {
    headers[CSRF_HEADER] = await ensureCsrfToken();
  }

  return headers;
}

async function fetchWithAuth(path: string, options: RequestInit = {}): Promise<Response> {
  let headers = await buildHeaders(options, (options.headers as Record<string, string>) ?? {});

  let res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: FETCH_CREDENTIALS,
  });

  if (res.status === 403) {
    const body = await res.clone().json().catch(() => ({}));
    if (body?.code === 'CSRF_INVALID') {
      await ensureCsrfToken(true);
      headers = await buildHeaders(options, (options.headers as Record<string, string>) ?? {});
      res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
        credentials: FETCH_CREDENTIALS,
      });
    }
  }

  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers = await buildHeaders(options, (options.headers as Record<string, string>) ?? {});
      res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
        credentials: FETCH_CREDENTIALS,
      });
    }
  }

  return res;
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetchWithAuth(path, options);

  if (res.status === 204) {
    return undefined as T;
  }

  const data = await res.json();

  if (!res.ok) {
    throw new Error(formatApiErrorBody(data));
  }

  return data as T;
}

export async function uploadFile<T = unknown>(
  path: string,
  file: File
): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetchWithAuth(path, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(formatApiErrorBody(data));
  }

  return res.json();
}

export async function fetchDocumentBlob(path: string): Promise<Blob> {
  const res = await fetchWithAuth(path);

  if (!res.ok) {
    throw new Error('Failed to load file');
  }

  return res.blob();
}

export function uploadFileWithProgress<T = unknown>(
  path: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return ensureCsrfToken().then((token) => new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', file);

    xhr.open('POST', `${API_BASE}${path}`);
    xhr.withCredentials = true;
    xhr.setRequestHeader(CSRF_HEADER, token);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      let data: ApiErrorPayload = {};
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        data = {};
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data as T);
        return;
      }
      reject(new Error(formatApiErrorBody(data)));
    };

    xhr.onerror = () => reject(new Error('Upload failed'));
    xhr.send(formData);
  }));
}

/**
 * SSE streaming request — returns a ReadableStream for manual processing.
 */
export async function streamRequest(
  path: string,
  body: unknown,
  signal?: AbortSignal
): Promise<Response> {
  return fetchWithAuth(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
}
