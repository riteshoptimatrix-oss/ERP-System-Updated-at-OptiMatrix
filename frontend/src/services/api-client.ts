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

    try {
      const response = await fetch(url, {
        credentials: 'include', // Automatically send and receive HttpOnly session cookies
        ...options,
        headers,
      });

      const contentType = response.headers.get('content-type');
      let responseData: unknown = null;

      if (contentType && contentType.includes('application/json')) {
        responseData = await response.json();
      }

      if (!response.ok) {
        const errorBody = responseData as { error?: ApiError } | null;
        const errorData: ApiError = errorBody?.error || {
          code: response.status,
          message: response.statusText || 'Request failed',
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
