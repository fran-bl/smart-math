'use client';

import { useEffect, useRef } from 'react';

import { getToken } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { getJwtExpiryMs, isJwtExpired } from '@/lib/utils/jwt';

/**
 * - validate token on app start
 * - auto-logout when JWT expires
 */
export default function AuthBootstrap() {
    const logout = useAuthStore((s) => s.logout);
    const checkAuth = useAuthStore((s) => s.checkAuth);
    const isHydrated = useAuthStore((s) => s.isHydrated);

    const logoutTimerRef = useRef<number | null>(null);

    useEffect(() => {
        if (!isHydrated) return;
        void checkAuth();
    }, [isHydrated, checkAuth]);

    useEffect(() => {
        const clearTimer = () => {
            if (logoutTimerRef.current) {
                window.clearTimeout(logoutTimerRef.current);
                logoutTimerRef.current = null;
            }
        };

        const schedule = () => {
            clearTimer();
            const token = getToken();
            if (!token) return;

            if (isJwtExpired(token)) {
                logout();
                return;
            }

            const expMs = getJwtExpiryMs(token);
            if (!expMs) return;

            const delay = Math.max(0, expMs - Date.now());
            logoutTimerRef.current = window.setTimeout(() => {
                logout();
            }, delay);
        };

        if (typeof window === 'undefined') return;

        schedule();

        const onLogoutEvent = () => {
            logout();
        };

        const onVisibility = () => {
            if (document.visibilityState === 'visible') {
                void checkAuth();
                schedule();
            }
        };

        window.addEventListener('auth:logout', onLogoutEvent as EventListener);
        document.addEventListener('visibilitychange', onVisibility);

        return () => {
            clearTimer();
            window.removeEventListener('auth:logout', onLogoutEvent as EventListener);
            document.removeEventListener('visibilitychange', onVisibility);
        };
    }, [logout, checkAuth]);

    return null;
}


