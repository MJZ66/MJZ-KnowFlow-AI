/**
 * HTTP client wrapper with JWT token management.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

interface ApiErrorPayload {
  code?: string;
  message?: string;
  message_en?: string;
  detail?: string;
}

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

function getTokens(): { access: string | null; refresh: string | null } {
  return {
    access: localStorage.getItem('access_token'),
    refresh: localStorage.getItem('refresh_token'),
  };
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}

export function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

async function refreshAccessToken(): Promise<string | null> {
  const { refresh } = getTokens();
  if (!refresh) return null;

  try {
    const res = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    return null;
  }
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const { access } = getTokens();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (access) {
    headers['Authorization'] = `Bearer ${access}`;
  }

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  let res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  // Try refresh on 401
  if (res.status === 401 && access) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      headers['Authorization'] = `Bearer ${newAccess}`;
      res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
      });
    }
  }

  // Handle 204 No Content
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
  const { access } = getTokens();
  const formData = new FormData();
  formData.append('file', file);

  let res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${access}`,
    },
    body: formData,
  });

  if (res.status === 401 && access) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${newAccess}`,
        },
        body: formData,
      });
    }
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(formatApiErrorBody(data));
  }

  return res.json();
}

export function uploadFileWithProgress<T = unknown>(
  path: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const { access } = getTokens();
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', file);

    xhr.open('POST', `${API_BASE}${path}`);
    if (access) {
      xhr.setRequestHeader('Authorization', `Bearer ${access}`);
    }

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
  });
}

/**
 * SSE streaming request — returns a ReadableStream for manual processing.
 */
export function streamRequest(
  path: string,
  body: unknown,
  signal?: AbortSignal
): Promise<Response> {
  const { access } = getTokens();

  return fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${access}`,
    },
    body: JSON.stringify(body),
    signal,
  });
}
