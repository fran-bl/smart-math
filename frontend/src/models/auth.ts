import { User } from './user';

export interface StudentLoginRequest {
    username: string;
    classCode: string; // Class code formed from emoji password (e.g., "ABCD")
}

export interface TeacherLoginRequest {
    username: string;
    password: string;
}

export type LoginRequest =
    | { role: 'student'; data: StudentLoginRequest }
    | { role: 'teacher'; data: TeacherLoginRequest };

// Backend JWT token response from /auth/my-token
export interface TokenResponse {
    access_token: string;
    token_type: string;
}

// Decoded JWT payload
export interface JWTPayload {
    sub: string; // username
    id: string; // user id
    exp: number; // expiration timestamp
}

// User info from /auth/me
export interface MeResponse {
    username: string;
    role: 'student' | 'teacher';
}

export interface AuthResponse {
    success: boolean;
    user?: User;
    token?: string;
    error?: string;
}

export interface AuthState {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
}

export interface AuthActions {
    login: (request: LoginRequest) => Promise<boolean>;
    logout: () => void;
    clearError: () => void;
    setLoading: (loading: boolean) => void;
}
