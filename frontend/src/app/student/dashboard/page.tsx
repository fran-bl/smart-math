'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { Spinner } from '@/components';
import { useAuthStore } from '@/lib/store';

export default function StudentDashboard() {
    const router = useRouter();
    const { user, isAuthenticated, isHydrated, logout } = useAuthStore();

    // Redirect to login if not authenticated
    useEffect(() => {
        if (isHydrated && (!isAuthenticated || !user)) {
            router.push('/');
        }
    }, [isHydrated, isAuthenticated, user, router]);

    // Redirect teachers to their dashboard
    useEffect(() => {
        if (isHydrated && user && user.role === 'teacher') {
            router.push('/teacher/dashboard');
        }
    }, [isHydrated, user, router]);

    const handleLogout = () => {
        logout();
        router.push('/');
    };

    // Show loading while hydrating or redirecting
    if (!isHydrated || !isAuthenticated || !user || user.role !== 'student') {
        return (
            <main className="min-h-screen flex items-center justify-center">
                <Spinner />
            </main>
        );
    }

    return (
        <main className="min-h-screen relative">
            {/* Header with user info */}
            <header className="absolute top-0 left-0 right-0 p-4 sm:p-6 flex justify-end items-center">
                <div className="flex items-center gap-3 sm:gap-4">
                    <div className="flex items-center gap-2 px-3 py-2 rounded-xl" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)' }}>
                        <span className="text-xl">👤</span>
                        <span className="font-medium">{user.username}</span>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="btn btn-outline flex items-center gap-2 !py-2 !px-4"
                    >
                        <span>Odjava</span>
                        <span className="text-lg">🚪</span>
                    </button>
                </div>
            </header>

            {/* Start game */}
            <div className="min-h-screen flex flex-col items-center justify-center p-8">
                <div className="text-center mb-8">
                    <div className="text-5xl mb-4">👋</div>
                    <h1 className="text-2xl font-bold mb-2">Bok, {user.username}!</h1>
                    <p className="text-gray-500 dark:text-gray-400">
                        Spreman za nove matematičke izazove?
                    </p>
                </div>

                <button
                    className="btn btn-primary text-xl px-10 py-4"
                >
                    🎮 Započni igru
                </button>
            </div>
        </main>
    );
}
