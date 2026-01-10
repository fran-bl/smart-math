import { isJwtExpired } from '@/lib/utils/jwt';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
    constructor(
        message: string,
        public status: number,
        public code?: string
    ) {
        super(message);
        this.name = 'ApiError';
    }
}

interface RequestOptions extends RequestInit {
    timeout?: number;
}

/**
 * Base API client for making HTTP requests
 */
export async function apiClient<T>(
    endpoint: string,
    options: RequestOptions = {}
): Promise<T> {
    const { timeout = 10000, ...fetchOptions } = options;

    const url = `${API_BASE_URL}${endpoint}`;

    // Get token from localStorage if available
    const token = typeof window !== 'undefined'
        ? localStorage.getItem('auth_token')
        : null;

    const clearSessionAndBroadcastLogout = (reason: 'expired' | 'unauthorized') => {
        if (typeof window === 'undefined') return;
        try {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth-storage');
            sessionStorage.clear();
        } catch {
            // ignore
        }
        try {
            window.dispatchEvent(new CustomEvent('auth:logout', { detail: { reason } }));
        } catch {
            // ignore
        }
    };

    if (token && isJwtExpired(token)) {
        clearSessionAndBroadcastLogout('expired');
        throw new ApiError('Sesija je istekla. Molimo prijavite se ponovno.', 401, 'TOKEN_EXPIRED');
    }

    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (token) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            ...fetchOptions,
            headers,
            signal: controller.signal,
        });

        clearTimeout(timeoutId);

        let data: any = null;
        try {
            data = await response.json();
        } catch {
            try {
                data = await response.text();
            } catch {
                data = null;
            }
        }

        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                clearSessionAndBroadcastLogout('unauthorized');
            }
            const message =
                (typeof data === 'string' && data) ||
                data?.message ||
                data?.error ||
                data?.detail ||
                response.statusText ||
                'Došlo je do greške';
            throw new ApiError(
                message,
                response.status,
                data?.code
            );
        }

        return data as T;
    } catch (error) {
        clearTimeout(timeoutId);

        if (error instanceof ApiError) {
            throw error;
        }

        if (error instanceof Error) {
            if (error.name === 'AbortError') {
                throw new ApiError('Zahtjev je istekao', 408, 'TIMEOUT');
            }
            throw new ApiError(
                'Nije moguće spojiti se na server',
                0,
                'NETWORK_ERROR'
            );
        }

        throw new ApiError('Nepoznata greška', 0, 'UNKNOWN');
    }
}

export const api = {
    get: <T>(endpoint: string, options?: RequestOptions) =>
        apiClient<T>(endpoint, { ...options, method: 'GET' }),

    post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
        apiClient<T>(endpoint, {
            ...options,
            method: 'POST',
            body: body ? JSON.stringify(body) : undefined,
        }),

    put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
        apiClient<T>(endpoint, {
            ...options,
            method: 'PUT',
            body: body ? JSON.stringify(body) : undefined,
        }),

    delete: <T>(endpoint: string, options?: RequestOptions) =>
        apiClient<T>(endpoint, { ...options, method: 'DELETE' }),
};

