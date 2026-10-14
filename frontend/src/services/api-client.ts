import { env } from '@/lib/env';
import { ApiResponse, ApiError } from '@/types/api';

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = env.apiUrl;
  }

  /**
   * Generic request handler with error encapsulation, timeouts, and headers.
   */
  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const normalizedPath = cleanEndpoint.startsWith('/api/v1')
      ? cleanEndpoint
      : `/api/v1${cleanEndpoint}`;
    const base = this.baseUrl.replace(/\/+$/, '').replace(/\/api\/v1\/?$/, '');
    const url = `${base}${normalizedPath}`;

    const headers = new Headers(options.headers || {});
    headers.set('Content-Type', 'application/json');

    // Extract CSRF token from document cookie in browser context if present
    if (typeof document !== 'undefined') {
      const match = document.cookie.match(/(?:^|; )RG_csrf=([^;]*)/);
      if (match && match[1]) {
        headers.set('X-CSRF-Token', decodeURIComponent(match[1]));
      }
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    try {
      const response = await fetch(url, {
        credentials: 'include', // Automatically send and receive HttpOnly session cookies
        ...options,
        signal: options.signal || controller.signal,
        headers,
      });
      clearTimeout(timeoutId);

      const contentType = response.headers.get('content-type');
      let responseData: unknown = null;

      if (contentType && contentType.includes('application/json')) {
        responseData = await response.json();
      }

      if (!response.ok) {
        const errorBody = responseData as { error?: ApiError; detail?: string | any } | null;
        let errorMessage = response.statusText || 'Request failed';
        if (errorBody?.error?.message) {
          errorMessage = errorBody.error.message;
        } else if (typeof errorBody?.detail === 'string') {
          errorMessage = errorBody.detail;
        } else if (Array.isArray(errorBody?.detail)) {
          errorMessage = errorBody.detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
        }
        const errorData: ApiError = {
          code: response.status,
          message: errorMessage,
        };
        return {
          status: response.status,
          error: errorData,
        };
      }

      return {
        status: response.status,
        data: responseData as T,
      };
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Network connection failed. Backend may be offline.';
      return {
        status: 0,
        error: {
          code: 0,
          message: errorMessage,
        },
      };
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async get<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  async post<T>(endpoint: string, body: unknown, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async put<T>(endpoint: string, body: unknown, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  async patch<T>(endpoint: string, body: unknown, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  }

  async delete<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
