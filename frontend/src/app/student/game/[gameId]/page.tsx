'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { Spinner } from '@/components';
import { disconnectSocket, getAuthedSocket } from '@/lib/realtime/socket';
import { useAuthStore } from '@/lib/store';

type QuestionPayload = {
    question_id: string;
    question: string;
    difficulty: number;
    type: 'num' | 'mcq' | 'wri';
    answer?: any;
};

type ReceiveQuestionsPayload = {
    game_id: string;
    topic_id: string;
    round_id?: string;
    questions: QuestionPayload[];
};

export default function StudentGamePage() {
    const router = useRouter();
    const params = useParams();
    const { user, isAuthenticated, isHydrated, logout } = useAuthStore();
    const gameId = String(params?.gameId ?? '');

    const [payload, setPayload] = useState<ReceiveQuestionsPayload | null>(null);
    const [startedAt, setStartedAt] = useState<number>(Date.now());
    const [answer, setAnswer] = useState<string>('');
    const [error, setError] = useState<string | null>(null);

    const currentQuestion = useMemo(() => payload?.questions?.[0] ?? null, [payload]);

    useEffect(() => {
        if (isHydrated && (!isAuthenticated || !user)) router.push('/');
    }, [isHydrated, isAuthenticated, user, router]);

    useEffect(() => {
        if (isHydrated && user && user.role !== 'student') {
            router.push(user.role === 'teacher' ? '/teacher/dashboard' : '/');
        }
    }, [isHydrated, user, router]);

    // Load payload from sessionStorage (set by JoinGameModal upon receiveQuestions)
    useEffect(() => {
        try {
            const raw = sessionStorage.getItem(`game_payload_${gameId}`);
            if (raw) {
                const parsed = JSON.parse(raw) as ReceiveQuestionsPayload;
                setPayload({
                    ...parsed,
                    game_id: String(parsed.game_id),
                    topic_id: String(parsed.topic_id),
                });
                setStartedAt(Date.now());
            }
        } catch {
            // ignore
        }
    }, [gameId]);

    // If payload isn't available yet (e.g. refresh), listen for receiveQuestions on the existing socket.
    useEffect(() => {
        if (payload) return;
        const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
        if (!token) return;

        const socket = getAuthedSocket(token);
        const handleClosed = () => {
            setError('Igra je završena');
            try {
                localStorage.removeItem('joined_game_code');
                sessionStorage.removeItem(`game_payload_${gameId}`);
            } catch {
                // ignore
            }
            router.push('/student/dashboard');
        };
        const handler = (data: any) => {
            const incomingGameId = String(data?.game_id ?? '');
            if (incomingGameId && incomingGameId === String(gameId)) {
                try {
                    sessionStorage.setItem(`game_payload_${incomingGameId}`, JSON.stringify(data));
                } catch {
                    // ignore
                }
                setPayload(data as ReceiveQuestionsPayload);
                setStartedAt(Date.now());
            }
        };

        socket.on('receiveQuestions', handler);
        socket.on('gameClosed', handleClosed);

        return () => {
            socket.off('receiveQuestions', handler);
            socket.off('gameClosed', handleClosed);
        };
    }, [gameId, payload]);

    const handleSubmit = async () => {
        setError(null);
        const token = localStorage.getItem('auth_token');
        if (!token) {
            setError('Niste prijavljeni');
            return;
        }
        if (!payload || !currentQuestion) return;

        const socket = getAuthedSocket(token);
        const roundId = payload.round_id;
        if (!roundId) {
            setError('Nedostaje round_id (backend mora poslati round_id u receiveQuestions)');
            return;
        }

        const timeSpentSecs = Math.max(0, Math.round((Date.now() - startedAt) / 1000));

        // Basic correctness check (best-effort)
        let isCorrect = false;
        if (currentQuestion.type === 'num') {
            const expected = Number(currentQuestion.answer?.correct_answer);
            isCorrect = Number(answer) === expected;
        } else if (currentQuestion.type === 'wri') {
            const expected = String(currentQuestion.answer?.correct_answer ?? '').trim().toLowerCase();
            isCorrect = answer.trim().toLowerCase() === expected;
        } else if (currentQuestion.type === 'mcq') {
            const expected = String(currentQuestion.answer?.correct_answer ?? '').trim().toLowerCase();
            isCorrect = answer.trim().toLowerCase() === expected;
        }

        socket.emit('submit_answer', {
            round_id: roundId,
            question_id: currentQuestion.question_id,
            is_correct: isCorrect,
            time_spent_secs: timeSpentSecs,
            hints_used: 0,
            num_attempts: 1,
        });

        // For now just show local confirmation
        setError(isCorrect ? 'Točno!' : 'Netočno!');
    };

    const handleLeaveGame = () => {
        // Leave the current game without logging out.
        disconnectSocket(); // triggers backend disconnect -> deactivates player
        try {
            localStorage.removeItem('joined_game_code');
            sessionStorage.removeItem(`game_payload_${gameId}`);
        } catch {
            // ignore
        }
        router.push('/student/dashboard');
    };

    if (!isHydrated || !isAuthenticated || !user || user.role !== 'student') {
        return (
            <main className="min-h-screen flex items-center justify-center">
                <Spinner />
            </main>
        );
    }

    return (
        <main className="min-h-screen p-4 sm:p-8 max-w-2xl mx-auto pb-12">
            <header className="flex justify-end mb-6">
                <button onClick={handleLeaveGame} className="btn btn-outline !py-2 !px-4">
                    Izađi iz igre
                </button>
            </header>

            <div className="card p-6 sm:p-8">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                    Pitanje 1
                </p>

                {error && (
                    <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                        <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
                    </div>
                )}

                {!currentQuestion ? (
                    <div className="flex flex-col items-center justify-center py-10 gap-3">
                        <Spinner />
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            Učitavam pitanja…
                        </p>
                    </div>
                ) : (
                    <>
                        <div className="mb-6">
                            <p className="text-lg font-medium">{currentQuestion.question}</p>

                        </div>

                        <div className="mb-4">
                            <input
                                value={answer}
                                onChange={(e) => setAnswer(e.target.value)}
                                className="w-full px-4 py-3 rounded-xl border bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 outline-none"
                                placeholder="Upiši odgovor…"
                            />
                        </div>

                        <button
                            onClick={handleSubmit}
                            className="btn btn-primary w-full py-3"
                        >
                            Pošalji odgovor
                        </button>
                    </>
                )}
            </div>
        </main>
    );
}


