'use client';

import Link from 'next/link';

export default function StudentDashboard() {
    return (
        <main className="min-h-screen flex items-center justify-center p-8">
            <div className="card p-10 max-w-lg w-full">
                {/* Header */}
                <div className="text-center mb-10">
                    <div className="text-5xl mb-4">👋</div>
                    <h1 className="text-2xl font-bold mb-2">Bok!</h1>
                    <p className="text-gray-500 dark:text-gray-400">
                        Spreman za nove matematičke izazove?
                    </p>
                </div>

                {/* Actions */}
                <div className="space-y-4">

                    <Link
                        href="/"
                        className="btn btn-outline w-full block text-center"
                    >
                        ← Natrag
                    </Link>
                </div>
            </div>
        </main>
    );
}

