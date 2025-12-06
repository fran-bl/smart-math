'use client';

import Link from 'next/link';
import { useState } from 'react';

export default function LoginPage() {
    const [isTeacherMode, setIsTeacherMode] = useState(false);

    const dashboardPath = isTeacherMode ? '/teacher/dashboard' : '/student/dashboard';

    return (
        <main className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-20 -left-20 w-72 h-72 bg-indigo-500/10 rounded-full blur-3xl" />
                <div className="absolute -bottom-20 -right-20 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
            </div>

            <div className="card p-8 sm:p-10 max-w-md w-full relative z-10">


                {/* Login Button */}
                <Link
                    href={dashboardPath}
                    className={`btn w-full block text-center text-lg py-4
                                ${isTeacherMode ? 'btn-secondary' : 'btn-primary'}`}
                >
                    {isTeacherMode ? '👨‍🏫 Prijavi se kao profesor' : '🚀 Prijavi se'}
                </Link>

                {/* Teacher Mode Toggle - Bottom Right */}
                <div className="absolute -bottom-16 right-0 flex items-center gap-3">
                    <span className="text-xs text-gray-400">Profesor?</span>
                    <button
                        onClick={() => setIsTeacherMode(!isTeacherMode)}
                        className={`relative w-14 h-7 rounded-full transition-all duration-300 
                                    ${isTeacherMode
                                ? 'bg-emerald-500'
                                : 'bg-gray-300 dark:bg-gray-600'}`}
                    >
                        <span
                            className={`absolute top-1 w-5 h-5 rounded-full bg-white shadow-md 
                                        transition-all duration-300
                                        ${isTeacherMode ? 'left-8' : 'left-1'}`}
                        />
                    </button>
                </div>
            </div>


        </main>
    );
}
