import {
    getCurrentUser,
    getToken,
    loginStudent,
    loginTeacher,
    logout as logoutApi,
    registerUser,
} from '@/lib/api';
import { User } from '@/models';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
    // State
    user: User | null;
    isAuthenticated: boolean;
    token: string | null;
    isLoading: boolean;
    isHydrated: boolean;
    error: string | null;

    // Actions
    loginAsStudent: (username: string, classCode: string) => Promise<boolean>;
    loginAsTeacher: (username: string, password: string) => Promise<boolean>;
    register: (username: string, role: 'student' | 'teacher', password?: string) => Promise<boolean>;
    logout: () => void;
    clearError: () => void;
    setLoading: (loading: boolean) => void;
    checkAuth: () => Promise<boolean>;
    setHydrated: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            // Initial state
            user: null,
            isAuthenticated: false,
            token: null,
            isLoading: false,
            isHydrated: false,
            error: null,

            // Set hydrated after store rehydrates from localStorage
            setHydrated: () => {
                set({ isHydrated: true });
            },

            // Check if user is authenticated (verify token and fetch user info)
            checkAuth: async () => {
                const token = getToken();
                if (!token) {
                    set({ user: null, isAuthenticated: false, token: null });
                    return false;
                }

                try {
                    const userInfo = await getCurrentUser();
                    if (userInfo) {
                        set({
                            user: {
                                id: '', // We don't get id from /me, but we have it in token
                                username: userInfo.username,
                                role: userInfo.role,
                            },
                            isAuthenticated: true,
                            token,
                        });
                        return true;
                    }
                } catch {
                    set({ user: null, isAuthenticated: false, token });
                }
                return false;
            },

            // Login as student with class code (emoji password)
            loginAsStudent: async (username: string, classCode: string) => {
                set({ isLoading: true, error: null });

                try {
                    const response = await loginStudent({ username, classCode });

                    if (response.success && response.token) {
                        // Fetch user info after successful login
                        const userInfo = await getCurrentUser();

                        if (userInfo) {
                            set({
                                user: {
                                    id: '',
                                    username: userInfo.username,
                                    role: userInfo.role,
                                },
                                isAuthenticated: true,
                                token: response.token,
                                isLoading: false,
                                error: null,
                            });
                            return true;
                        }

                        // Keep token, but surface a clear error if /me failed
                        set({
                            isAuthenticated: false,
                            token: response.token,
                            isLoading: false,
                            error: 'Prijava je uspjela, ali nije moguće dohvatiti profil (/auth/me)',
                        });
                        return false;
                    }

                    set({
                        isLoading: false,
                        error: response.error || 'Prijava nije uspjela',
                    });
                    return false;
                } catch {
                    set({
                        isLoading: false,
                        error: 'Došlo je do greške prilikom prijave',
                    });
                    return false;
                }
            },

            // Login as teacher
            loginAsTeacher: async (username: string, password: string) => {
                set({ isLoading: true, error: null });

                try {
                    const response = await loginTeacher({ username, password });

                    if (response.success && response.token) {
                        // Fetch user info after successful login
                        const userInfo = await getCurrentUser();

                        if (userInfo) {
                            set({
                                user: {
                                    id: '',
                                    username: userInfo.username,
                                    role: userInfo.role,
                                },
                                isAuthenticated: true,
                                token: response.token,
                                isLoading: false,
                                error: null,
                            });
                            return true;
                        }

                        set({
                            isAuthenticated: false,
                            token: response.token,
                            isLoading: false,
                            error: 'Prijava je uspjela, ali nije moguće dohvatiti profil (/auth/me)',
                        });
                        return false;
                    }

                    set({
                        isLoading: false,
                        error: response.error || 'Prijava nije uspjela',
                    });
                    return false;
                } catch {
                    set({
                        isLoading: false,
                        error: 'Došlo je do greške prilikom prijave',
                    });
                    return false;
                }
            },

            // Register new user
            register: async (username: string, role: 'student' | 'teacher', password?: string) => {
                set({ isLoading: true, error: null });

                try {
                    const response = await registerUser({ username, role, password });

                    if (response.success) {
                        set({ isLoading: false, error: null });
                        return true;
                    }

                    set({
                        isLoading: false,
                        error: response.error || 'Registracija nije uspjela',
                    });
                    return false;
                } catch {
                    set({
                        isLoading: false,
                        error: 'Došlo je do greške prilikom registracije',
                    });
                    return false;
                }
            },

            // Logout
            logout: () => {
                logoutApi();
                set({
                    user: null,
                    isAuthenticated: false,
                    token: null,
                    error: null,
                });
            },

            // Clear error
            clearError: () => {
                set({ error: null });
            },

            // Set loading state
            setLoading: (loading: boolean) => {
                set({ isLoading: loading });
            },
        }),
        {
            name: 'auth-storage', // localStorage key
            partialize: (state) => ({
                // Only persist user data, not loading/error states
                user: state.user,
                isAuthenticated: state.isAuthenticated,
                token: state.token,
            }),
            onRehydrateStorage: () => (state) => {
                state?.setHydrated();
            },
        }
    )
);
