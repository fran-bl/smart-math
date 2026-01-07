'use client';

import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';

import { Spinner } from '@/components';
import { useAuthStore } from '@/lib/store';

export default function TeacherGamePage() {
    const router = useRouter();
    const search = useSearchParams();
    const params = useParams();
    const { user, isAuthenticated, isHydrated } = useAuthStore();

    const gameId = String(params?.gameId ?? '');
    const topicName = search.get('topicName') || '';
    const classroomId = search.get('classroomId') || '';

    const [players, setPlayers] = useState<string[]>([]);
    const [playersDetailed, setPlayersDetailed] = useState<
        Array<{ user_id: string; username: string; level: number; xp: number; rank: number }>
    >([]);
    const [isConnecting, setIsConnecting] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [hasStarted] = useState(true);
    const [isEnding, setIsEnding] = useState(false);
    const [overrideLoading, setOverrideLoading] = useState<Record<string, 'up' | 'down' | null>>({});
    const [overrideEligible, setOverrideEligible] = useState<Record<string, boolean>>({});
    const [classroomName, setClassroomName] = useState<string>('');
    const socketRef = useRef<Socket | null>(null);
    const lastOverrideRefreshAtRef = useRef<number>(0);

    const dlog = (...args: any[]) => {
        try {
            if (typeof window !== 'undefined' && localStorage.getItem('debug_logs') === '1') {
                console.log('[teacher-game]', ...args);
            }
        } catch {
            // ignore
        }
    };

    const refreshOverrideEligible = async (token: string, classroomNameToUse: string) => {
        if (!token || !classroomNameToUse) return;
        const now = Date.now();
        if (now - lastOverrideRefreshAtRef.current < 1500) return;
        lastOverrideRefreshAtRef.current = now;

        try {
            const res = await fetch(
                `http://localhost:8000/override/recommendations/${encodeURIComponent(classroomNameToUse)}`,
                { headers: { Authorization: `Bearer ${token}` } },
            );
            if (!res.ok) return;
            const data = (await res.json()) as Array<any>;
            const map: Record<string, boolean> = {};
            for (const r of data || []) {
                const username = String(r?.student ?? '');
                if (!username) continue;
                map[username] = Boolean(r?.last_recommendation);
            }
            setOverrideEligible(map);
            dlog('overrideEligible', map);
        } catch {
            // ignore
        }
    };

    // Auth guards
    useEffect(() => {
        if (isHydrated && (!isAuthenticated || !user)) {
            router.push('/');
        }
    }, [isHydrated, isAuthenticated, user, router]);

    useEffect(() => {
        if (isHydrated && user && user.role !== 'teacher') {
            router.push(user.role === 'student' ? '/student/dashboard' : '/');
        }
    }, [isHydrated, user, router]);

    // Live players list
    useEffect(() => {
        if (!isHydrated || !isAuthenticated || !user || user.role !== 'teacher') return;
        if (!gameId) return;

        const token = localStorage.getItem('auth_token');
        if (!token) {
            setError('Niste prijavljeni');
            setIsConnecting(false);
            return;
        }

        const socket = io('http://localhost:8000', {
            transports: ['polling', 'websocket'],
            withCredentials: true,
            auth: { token },
            extraHeaders: { Authorization: `Bearer ${token}` },
        });

        socketRef.current = socket;
        socket.on('connect', () => {
            setIsConnecting(false);
            setError(null);
            socket.emit('teacherJoin', { game_id: gameId, mode: 'game' });
        });

        socket.on('connect_error', () => {
            setError('Greška pri povezivanju');
            setIsConnecting(false);
        });

        socket.on('updatePlayers', (data: { players?: string[]; playersDetailed?: any[] }) => {
            dlog('updatePlayers', { players: data?.players?.length, detailed: data?.playersDetailed?.length });
            setPlayers(data?.players ?? []);
            if (Array.isArray(data?.playersDetailed)) {
                setPlayersDetailed(
                    data.playersDetailed
                        .filter((p) => p && typeof p === 'object')
                        .map((p: any) => ({
                            user_id: String(p.user_id ?? ''),
                            username: String(p.username ?? ''),
                            level: Number(p.level ?? 1),
                            xp: Number(p.xp ?? 0),
                            rank: Number(p.rank ?? 0),
                        }))
                        .filter((p) => p.user_id && p.username),
                );
            } else {
                setPlayersDetailed([]);
            }

            if (classroomName) void refreshOverrideEligible(token, classroomName);
        });

        socket.on('gameClosed', () => {
            setError('Igra je zatvorena');
        });

        socket.on('error', (data: { message?: string }) => {
            setError(data?.message || 'Greška');
        });

        return () => {
            // End game
            try {
                socket.emit('endGame', { game_id: gameId });
            } catch {
            }
            socket.disconnect();
            socketRef.current = null;
        };
    }, [isHydrated, isAuthenticated, user, gameId]);

    useEffect(() => {
        const token = localStorage.getItem('auth_token');
        if (!token || !classroomId) return;
        let cancelled = false;

        const run = async () => {
            try {
                const res = await fetch('http://localhost:8000/classroom/my-classrooms', {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!res.ok) return;
                const classrooms = (await res.json()) as Array<any>;
                const cls = classrooms?.find((c) => String(c?.id ?? '') === String(classroomId));
                const name = String(cls?.class_name ?? '');
                if (!cancelled && name) setClassroomName(name);
            } catch {
                // ignore
            }
        };

        run();
        return () => {
            cancelled = true;
        };
    }, [classroomId]);

    useEffect(() => {
        const token = localStorage.getItem('auth_token');
        if (!token || !classroomName) return;
        void refreshOverrideEligible(token, classroomName);
    }, [classroomName]);


    if (!isHydrated || !isAuthenticated || !user || user.role !== 'teacher') {
        return (
            <main className="min-h-screen flex items-center justify-center">
                <Spinner />
            </main>
        );
    }

    const handleEndGame = () => {
        setIsEnding(true);
        try {
            if (socketRef.current && socketRef.current.connected) {
                socketRef.current.emit('endGame', { game_id: gameId });
            }
        } catch {
            // ignore
        } finally {
            router.push('/teacher/dashboard');
        }
    };

    const handleOverride = async (studentUsername: string, direction: 'up' | 'down') => {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            setError('Niste prijavljeni');
            return;
        }
        if (!overrideEligible[studentUsername]) return;

        setOverrideLoading((m) => ({ ...m, [studentUsername]: direction }));
        setError(null);
        try {
            dlog('override click', { studentUsername, direction });
            const res = await fetch('http://localhost:8000/override/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    student_username: studentUsername,
                    action: direction === 'up' ? 'override_up' : 'override_down',
                }),
            });

            if (!res.ok) {
                let detail = '';
                try {
                    const json = await res.json();
                    detail = String(json?.detail ?? '');
                } catch {
                    // ignore
                }
                throw new Error(detail || `HTTP ${res.status}`);
            }
            dlog('override ok', { studentUsername, direction });

            try {
                socketRef.current?.emit('teacherJoin', { game_id: gameId, mode: 'game' });
            } catch {
                // ignore
            }
        } catch (e) {
            setError(`Override nije uspio: ${(e as Error).message}`);
        } finally {
            setOverrideLoading((m) => ({ ...m, [studentUsername]: null }));
        }
    };

    return (
        <main className="min-h-screen p-4 sm:p-8 max-w-3xl mx-auto pb-12">
            <div className="card p-6 sm:p-8">
                <div className="flex items-start justify-between gap-4 mb-6">
                    <div>
                        <h1 className="text-2xl font-bold">{topicName || 'Igra'}</h1>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            Učenici:
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleEndGame}
                            disabled={isEnding}
                            className="btn btn-outline !py-2 !px-4 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isEnding ? 'Prekidam…' : 'Prekini igru'}
                        </button>

                    </div>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                        <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
                    </div>
                )}

                {isConnecting ? (
                    <div className="flex items-center justify-center py-10">
                        <Spinner />
                    </div>
                ) : players.length === 0 ? (
                    <div className="text-center py-10 text-gray-500">
                        <p className="font-medium">Još nema prijavljenih učenika</p>
                    </div>
                ) : (
                    <div
                        className="rounded-xl border p-3"
                        style={{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }}
                    >
                        <div className="max-h-72 overflow-auto">
                            <ul className="space-y-2">
                                {(playersDetailed.length ? playersDetailed : players.map((p) => ({ user_id: p, username: p, level: 0, xp: 0, rank: 0 })))
                                    .sort((a, b) => (a.rank && b.rank ? a.rank - b.rank : 0))
                                    .map((p) => (
                                        <li key={p.user_id} className="flex items-center justify-between gap-3 font-medium p-2 rounded-lg">
                                            <div className="flex items-center gap-3 min-w-0">
                                                {p.rank ? (
                                                    <span className="w-8 text-center text-sm font-bold text-indigo-600 dark:text-indigo-400">
                                                        #{p.rank}
                                                    </span>
                                                ) : (
                                                    <span className="w-8" />
                                                )}
                                                <i className="fa-regular fa-user text-gray-400 dark:text-gray-500" />
                                                <span className="truncate">{p.username}</span>
                                            </div>
                                            {p.level ? (
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs px-2 py-1 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300">
                                                        Level {p.level}
                                                    </span>
                                                    <span className="text-xs text-gray-500 dark:text-gray-400 tabular-nums">
                                                        {p.xp} XP
                                                    </span>
                                                    {overrideEligible[p.username] ? (
                                                        <>
                                                            <button
                                                                onClick={() => handleOverride(p.username, 'down')}
                                                                disabled={
                                                                    (overrideLoading[p.username] !== undefined &&
                                                                        overrideLoading[p.username] !== null) ||
                                                                    (p.level ?? 1) <= 1
                                                                }
                                                                className="btn btn-outline !py-1 !px-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                                                title="Smanji level"
                                                            >
                                                                <i className="fa-solid fa-arrow-down" />
                                                            </button>
                                                            <button
                                                                onClick={() => handleOverride(p.username, 'up')}
                                                                disabled={
                                                                    (overrideLoading[p.username] !== undefined &&
                                                                        overrideLoading[p.username] !== null) ||
                                                                    (p.level ?? 1) >= 5
                                                                }
                                                                className="btn btn-outline !py-1 !px-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                                                title="Povećaj level"
                                                            >
                                                                <i className="fa-solid fa-arrow-up" />
                                                            </button>
                                                        </>
                                                    ) : null}
                                                </div>
                                            ) : null}
                                        </li>
                                    ))}
                            </ul>
                        </div>
                    </div>
                )}


            </div>
        </main>
    );
}


