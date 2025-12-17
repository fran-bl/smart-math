'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { CreateClassroomModal, Spinner } from '@/components';
import { useAuthStore } from '@/lib/store';

export default function TeacherDashboard() {
    const router = useRouter();
    const { user, isAuthenticated, isHydrated, logout } = useAuthStore();

    const [showCreateClassroom, setShowCreateClassroom] = useState(false);

    const students: { id: string; name: string; quizzes: number; avgScore: number }[] = [];

    // Redirect to login if not authenticated
    useEffect(() => {
        if (isHydrated && (!isAuthenticated || !user)) {
            router.push('/');
        }
    }, [isHydrated, isAuthenticated, user, router]);

    // Redirect students to their dashboard
    useEffect(() => {
        if (isHydrated && user && user.role === 'student') {
            router.push('/student/dashboard');
        }
    }, [isHydrated, user, router]);

    const handleLogout = () => {
        logout();
        router.push('/');
    };

    // Show loading while hydrating or redirecting
    if (!isHydrated || !isAuthenticated || !user || user.role !== 'teacher') {
        return (
            <main className="min-h-screen flex items-center justify-center">
                <Spinner />
            </main>
        );
    }

    return (
        <main className="min-h-screen relative">
            {/* Header */}
            <header className="absolute top-0 left-0 right-0 p-4 sm:p-6 flex justify-end items-center">
                <div className="flex items-center gap-3 sm:gap-4">
                    <div className="flex items-center gap-2 px-3 py-2 rounded-xl" style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)' }}>
                        <span className="text-xl">👨‍🏫</span>
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

            {/* Main content */}
            <div className="min-h-screen flex flex-col items-center justify-center p-8 pt-24">
                <div className="card p-6 sm:p-8 w-full max-w-3xl">
                    {/* Title */}
                    <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <div>
                            <h1 className="text-2xl font-bold mb-1">📚 Moj razred</h1>
                            <p className="text-gray-500 dark:text-gray-400 text-sm">
                                Pregled učenika i njihovog napretka
                            </p>
                        </div>
                        <button
                            onClick={() => setShowCreateClassroom(true)}
                            className="btn btn-secondary flex items-center gap-2 !py-2 !px-4"
                        >
                            <span className="text-lg">+</span>
                            <span>Novi razred</span>
                        </button>
                    </div>

                    {/* Students table */}
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b" style={{ borderColor: 'var(--card-border)' }}>
                                    <th className="text-left py-3 px-2 font-semibold">Učenik</th>
                                    <th className="text-center py-3 px-2 font-semibold">Kvizova</th>
                                    <th className="text-center py-3 px-2 font-semibold">Prosjek</th>
                                </tr>
                            </thead>
                            <tbody>
                                {students.map((student) => (
                                    <tr
                                        key={student.id}
                                        className="border-b last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                                        style={{ borderColor: 'var(--card-border)' }}
                                    >
                                        <td className="py-3 px-2">
                                            <div className="flex items-center gap-2">
                                                <span className="text-lg">👤</span>
                                                <span>{student.name}</span>
                                            </div>
                                        </td>
                                        <td className="text-center py-3 px-2">
                                            <span className="font-medium">{student.quizzes}</span>
                                        </td>
                                        <td className="text-center py-3 px-2">
                                            <span
                                                className="font-medium px-2 py-1 rounded-lg text-sm"
                                                style={{
                                                    background: student.avgScore >= 80
                                                        ? 'rgba(16, 185, 129, 0.15)'
                                                        : student.avgScore >= 60
                                                            ? 'rgba(245, 158, 11, 0.15)'
                                                            : 'rgba(239, 68, 68, 0.15)',
                                                    color: student.avgScore >= 80
                                                        ? 'var(--secondary)'
                                                        : student.avgScore >= 60
                                                            ? '#f59e0b'
                                                            : '#ef4444'
                                                }}
                                            >
                                                {student.avgScore}%
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Empty state placeholder */}
                    {students.length === 0 && (
                        <div className="text-center py-10 text-gray-500">
                            <p>Još nema učenika u razredu</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Create Classroom Modal */}
            <CreateClassroomModal
                isOpen={showCreateClassroom}
                onClose={() => setShowCreateClassroom(false)}
                onSuccess={() => {
                    // TODO: Refresh classroom list when implemented
                }}
            />
        </main>
    );
}
