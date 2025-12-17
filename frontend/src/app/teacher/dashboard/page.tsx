'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { CreateClassroomModal, Spinner } from '@/components';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { passwordToEmojis } from '@/lib/utils';

interface Classroom {
    id: string;
    class_name: string;
    class_code: string;
    student_count: number;
}

export default function TeacherDashboard() {
    const router = useRouter();
    const { user, isAuthenticated, isHydrated, logout } = useAuthStore();

    const [showCreateClassroom, setShowCreateClassroom] = useState(false);
    const [classrooms, setClassrooms] = useState<Classroom[]>([]);
    const [selectedClassroom, setSelectedClassroom] = useState<Classroom | null>(null);
    const [isLoadingClassrooms, setIsLoadingClassrooms] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch classrooms
    const fetchClassrooms = useCallback(async () => {
        setIsLoadingClassrooms(true);
        setError(null);
        try {
            const data = await api.get<Classroom[]>('/classroom/my-classrooms');
            setClassrooms(data);
            // Auto-select first classroom if none selected
            setSelectedClassroom(prev => {
                if (!prev && data.length > 0) {
                    return data[0];
                }
                // If previously selected classroom still exists, keep it
                if (prev) {
                    const stillExists = data.find(c => c.id === prev.id);
                    return stillExists || (data.length > 0 ? data[0] : null);
                }
                return prev;
            });
        } catch (err) {
            setError('Nije moguće učitati razrede');
            console.error(err);
        } finally {
            setIsLoadingClassrooms(false);
        }
    }, []);

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

    // Load classrooms when authenticated
    useEffect(() => {
        if (isHydrated && isAuthenticated && user?.role === 'teacher') {
            fetchClassrooms();
        }
    }, [isHydrated, isAuthenticated, user, fetchClassrooms]);

    const handleLogout = () => {
        logout();
        router.push('/');
    };

    const handleClassroomChange = (classroomId: string) => {
        const classroom = classrooms.find(c => c.id === classroomId);
        if (classroom) {
            setSelectedClassroom(classroom);
        }
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
        <main className="min-h-screen">
            {/* Header */}
            <header className="sticky top-0 z-10 p-4 sm:p-6 flex justify-end items-center" style={{ background: 'var(--background)' }}>
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
            <div className="p-4 sm:p-8 max-w-3xl mx-auto pb-12">
                <div className="card p-6 sm:p-8 w-full">
                    {/* Title */}
                    <div className="flex items-center gap-2 mb-4">
                        <h1 className="text-2xl font-bold">Moji razredi</h1>
                        <button
                            onClick={fetchClassrooms}
                            disabled={isLoadingClassrooms}
                            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 transition-colors"
                            title="Osvježi"
                        >
                            <span className={`text-xl ${isLoadingClassrooms ? 'animate-spin' : ''}`}>🔄</span>
                        </button>
                    </div>

                    {/* Classroom selector */}
                    <div className="flex items-center gap-3 mb-6">
                        {classrooms.length > 0 && (
                            <select
                                value={selectedClassroom?.id || ''}
                                onChange={(e) => handleClassroomChange(e.target.value)}
                                className="px-3 py-2 rounded-xl border bg-white dark:bg-gray-800 
                                           border-gray-200 dark:border-gray-700 
                                           focus:border-indigo-500 dark:focus:border-indigo-400 
                                           outline-none transition-colors font-medium"
                            >
                                {classrooms.map((classroom) => (
                                    <option key={classroom.id} value={classroom.id}>
                                        {classroom.class_name}
                                    </option>
                                ))}
                            </select>
                        )}
                        <button
                            onClick={() => setShowCreateClassroom(true)}
                            className="btn btn-secondary flex items-center gap-2 !py-2 !px-4"
                        >
                            <span className="text-lg">+</span>
                            <span>Novi razred</span>
                        </button>
                    </div>

                    {/* Error message */}
                    {error && (
                        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                            <p className="text-red-600 dark:text-red-400 text-sm">
                                {error}
                            </p>
                        </div>
                    )}

                    {/* Loading state */}
                    {isLoadingClassrooms ? (
                        <div className="flex items-center justify-center py-12">
                            <Spinner />
                        </div>
                    ) : classrooms.length === 0 ? (
                        /* Empty state - no classrooms */
                        <div className="text-center py-12 text-gray-500">
                            <p className="font-medium mb-2">Nemate nijedan razred</p>
                            <p className="text-sm">Kliknite "Novi razred" za kreiranje prvog razreda</p>
                        </div>
                    ) : selectedClassroom ? (
                        /* Selected classroom info */
                        <div className="space-y-2">
                            <p className="text-gray-600 dark:text-gray-400">
                                Šifra razreda: <span className="text-xl ml-2">{passwordToEmojis(selectedClassroom.class_code.split(''))}</span>
                            </p>
                            <p className="text-gray-600 dark:text-gray-400">
                                Broj učenika: <span className="font-semibold ml-2">{selectedClassroom.student_count}</span>
                            </p>

                            {/* Students placeholder */}
                            {selectedClassroom.student_count === 0 ? (
                                <div className="text-center py-8 text-gray-500 mt-6">
                                    <p className="font-medium mb-1">Nema učenika u razredu</p>
                                </div>
                            ) : (
                                <div className="text-center py-8 text-gray-500 mt-6">
                                    {/* TODO: ovdje dodati popis učenika */}
                                </div>
                            )}
                        </div>
                    ) : null}
                </div>
            </div>

            {/* Create Classroom Modal */}
            <CreateClassroomModal
                isOpen={showCreateClassroom}
                onClose={() => setShowCreateClassroom(false)}
                onSuccess={() => {
                    fetchClassrooms();
                }}
            />
        </main>
    );
}
