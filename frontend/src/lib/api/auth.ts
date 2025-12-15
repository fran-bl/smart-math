// Authentication API methods

import {
    MeResponse,
    StudentLoginRequest,
    TeacherLoginRequest,
    TokenResponse,
} from '@/models';
import { api, ApiError } from './client';

const TOKEN_KEY = 'auth_token';

// Request type for registration
interface RegisterRequest {
    username: string;
    role: 'student' | 'teacher';
    password?: string; // Only for teachers
}

/**
 * Register a new user
 * Calls POST /auth/ with username, role, and optionally password (for teachers)
 */
export async function registerUser(
    data: RegisterRequest
): Promise<{ success: boolean; error?: string }> {
    try {
        await api.post('/auth/', {
            username: data.username,
            role: data.role,
            password: data.role === 'teacher' ? data.password : null,
        });

        return { success: true };
    } catch (error) {
        if (error instanceof ApiError) {
            return {
                success: false,
                error: error.status === 400
                    ? 'Korisnik s tim imenom već postoji'
                    : error.message,
            };
        }
        return {
            success: false,
            error: 'Registracija nije uspjela. Pokušajte ponovo.',
        };
    }
}

/**
 * Login as a student with class code (emoji password)
 */
export async function loginStudent(
    credentials: StudentLoginRequest
): Promise<{ success: boolean; token?: string; error?: string }> {
    try {
        const response = await api.post<TokenResponse>('/auth/my-token', {
            username: credentials.username,
            class_code: credentials.classCode,
        });

        // Store token if login successful
        if (response.access_token) {
            localStorage.setItem(TOKEN_KEY, response.access_token);
            return { success: true, token: response.access_token };
        }

        return { success: false, error: 'Prijava nije uspjela' };
    } catch (error) {
        if (error instanceof ApiError) {
            return {
                success: false,
                error: error.status === 401
                    ? 'Pogrešno ime ili šifra razreda'
                    : error.message,
            };
        }
        return {
            success: false,
            error: 'Prijava nije uspjela. Pokušajte ponovo.',
        };
    }
}

/**
 * Login as a teacher with text password
 * Calls /auth/my-token with username and password
 */
export async function loginTeacher(
    credentials: TeacherLoginRequest
): Promise<{ success: boolean; token?: string; error?: string }> {
    try {
        const response = await api.post<TokenResponse>('/auth/my-token', {
            username: credentials.username,
            password: credentials.password,
        });

        // Store token if login successful
        if (response.access_token) {
            localStorage.setItem(TOKEN_KEY, response.access_token);
            return { success: true, token: response.access_token };
        }

        return { success: false, error: 'Prijava nije uspjela' };
    } catch (error) {
        if (error instanceof ApiError) {
            return {
                success: false,
                error: error.status === 401
                    ? 'Pogrešno korisničko ime ili lozinka'
                    : error.message,
            };
        }
        return {
            success: false,
            error: 'Prijava nije uspjela. Pokušajte ponovo.',
        };
    }
}

/**
 * Get current user info
 */
export async function getCurrentUser(): Promise<MeResponse | null> {
    try {
        const response = await api.get<MeResponse>('/auth/me');
        return response;
    } catch (error) {
        // If token is invalid, clear it
        logout();
        return null;
    }
}

/**
 * Logout - clear stored credentials
 */
export function logout(): void {
    localStorage.removeItem(TOKEN_KEY);
}

/**
 * Get stored token
 */
export function getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(TOKEN_KEY);
}

/**
 * Check if user has a stored token
 */
export function hasToken(): boolean {
    return !!getToken();
}
