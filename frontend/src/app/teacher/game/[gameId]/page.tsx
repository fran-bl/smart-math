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
        Array<{ user_id: string; username: string; level: number; xp: number; rank: number; last_recommendation?: string | null }>
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
    const overrideRefreshTimerRef = useRef<number | null>(null);

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
        const elapsed = now - lastOverrideRefreshAtRef.current;
        if (elapsed < 1500) {
            const waitMs = Math.max(0, 1500 - elapsed) + 50;
            if (overrideRefreshTimerRef.current) window.clearTimeout(overrideRefreshTimerRef.current);
            overrideRefreshTimerRef.current = window.setTimeout(() => {
                overrideRefreshTimerRef.current = null;
                void refreshOverrideEligible(token, classroomNameToUse);
            }, waitMs);
            return;
        }
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
            dlog('updatePlayers', { players: data?.players?.length, detailed: data?.playersDetailed?.length, classroomName });
            setPlayers(data?.players ?? []);
            if (Array.isArray(data?.playersDetailed)) {
                const mapped = data.playersDetailed
                    .filter((p) => p && typeof p === 'object')
                    .map((p: any) => ({
                        user_id: String(p.user_id ?? ''),
                        username: String(p.username ?? ''),
                        level: Number(p.level ?? 1),
                        previous_level: Number(p.previous_level ?? p.prev_level ?? p.level ?? 1),
                        xp: Number(p.xp ?? 0),
                        rank: Number(p.rank ?? 0),
                        accuracy: typeof p.accuracy === 'number' ? p.accuracy : null,
                        avg_time_secs: typeof p.avg_time_secs === 'number' ? p.avg_time_secs : null,
                        hints_used: typeof p.hints_used === 'number' ? p.hints_used : null,
                        last_recommendation: (p?.last_recommendation ?? p?.lastRecommendation ?? null) as any,
                    }))
                    .filter((p) => p.user_id && p.username);
                setPlayersDetailed(mapped);

                const hasRecField = (data.playersDetailed || []).some(
                    (p: any) => p && typeof p === 'object' && ('last_recommendation' in p || 'lastRecommendation' in p),
                );
                if (hasRecField) {
                    const map: Record<string, boolean> = {};
                    for (const p of mapped) {
                        map[p.username] = Boolean(p.last_recommendation);
                    }
                    setOverrideEligible(map);
                    dlog('overrideEligible(from socket)', map);
                    return;
                }
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
            if (overrideRefreshTimerRef.current) {
                window.clearTimeout(overrideRefreshTimerRef.current);
                overrideRefreshTimerRef.current = null;
            }
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

    const renderReason = (p: {
        level: number;
        previous_level: number;
        accuracy?: number | null;
        avg_time_secs?: number | null;
        hints_used?: number | null;
    }) => {
        if (p.level === p.previous_level) return null;

        const direction = p.level > p.previous_level ? 'povećali' : 'smanjili';

        const parts: string[] = [];

        if (typeof p.accuracy === 'number') {
            parts.push(`točnosti = ${Math.round(p.accuracy * 100)}%`);
        }

        if (typeof p.avg_time_secs === 'number') {
            parts.push(`prosječnog vremena po pitanju = ${p.avg_time_secs.toFixed(1)} s`);
        }

        if (typeof p.hints_used === 'number') {
            parts.push(`${p.hints_used} iskorištena hint-a`);
        }

        if (!parts.length) return null;

        return `Zbog ${parts.join(', ')} ${direction} smo razinu.`;
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
                        className="rounded-2xl border overflow-hidden"
                        style={{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }}
                    >
                        <div className="max-h-72 overflow-auto">
                            <table className="w-full text-sm border-collapse">
                                <thead
                                    className="sticky top-0 z-10 border-b"
                                    style={{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }}
                                >
                                    <tr className="text-left">
                                        <th className="py-3 px-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 text-center w-14">
                                            &nbsp;
                                        </th>
                                        <th className="py-3 px-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 text-center w-16">
                                            #
                                        </th>
                                        <th className="py-3 px-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 w-52">
                                            Ime
                                        </th>
                                        <th className="py-3 px-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 text-right w-24">
                                            XP
                                        </th>
                                        <th className="py-3 px-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 text-center w-28">
                                            Prijašnji lvl
                                        </th>
                                        <th className="py-3 px-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 text-center w-28">
                                            Trenutni lvl
                                        </th>
                                        <th className="py-3 px-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 w-[55%]">
                                            Razlog
                                        </th>
                                        <th className="py-3 px-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 text-center w-28">
                                            Override
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y" style={{ borderColor: 'var(--card-border)' }}>
                                    {(playersDetailed.length
                                        ? playersDetailed
                                        : players.map((p) => ({
                                            user_id: p,
                                            username: p,
                                        }))
                                    ).map((p: any) => (
                                        <tr
                                            key={p.user_id}
                                            className="hover:bg-gray-50/80 dark:hover:bg-gray-800/40"
                                        >
                                            {/* Avatar */}
                                            <td className="py-3 px-3 align-middle text-center">
                                                <span
                                                    className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-800 border"
                                                    style={{ borderColor: 'var(--card-border)' }}
                                                    aria-hidden="true"
                                                >
                                                    <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                                                        {String(p.username || '?').charAt(0).toUpperCase()}
                                                    </span>
                                                </span>
                                            </td>

                                            {/* Rank */}
                                            <td className="py-3 px-3 align-middle text-center tabular-nums text-gray-600 dark:text-gray-300">
                                                {typeof p.rank === 'number' && p.rank > 0 ? `#${p.rank}` : '—'}
                                            </td>

                                            {/* Ime */}
                                            <td className="py-3 px-3 align-middle">
                                                <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
                                                    {p.username}
                                                </div>
                                            </td>

                                            {/* XP */}
                                            <td className="py-3 px-3 align-middle tabular-nums text-right text-gray-900 dark:text-gray-100">
                                                {typeof p.xp === 'number' ? p.xp : '—'}
                                            </td>

                                            {/* Prijašnji level */}
                                            <td className="py-3 px-3 align-middle text-center">
                                                <span className="inline-flex items-center justify-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200">
                                                    {typeof p.previous_level === 'number' ? p.previous_level : '—'}
                                                </span>
                                            </td>

                                            {/* Trenutni level */}
                                            <td className="py-3 px-3 align-middle text-center">
                                                <span className="inline-flex items-center justify-center px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300">
                                                    {typeof p.level === 'number' ? p.level : '—'}
                                                </span>
                                            </td>

                                            {/* Razlog */}
                                            <td className="py-3 px-3 align-middle w-[55%]">
                                                <div className="text-xs leading-snug text-gray-600 dark:text-gray-300">
                                                    {renderReason(p) || <span className="text-gray-400">—</span>}
                                                </div>
                                            </td>

                                            {/* Strelica */}
                                            <td className="py-3 px-3 align-middle text-center">
                                                {overrideEligible[p.username] ? (
                                                    <div className="inline-flex items-center justify-center gap-2">
                                                        <button
                                                            onClick={() => handleOverride(p.username, 'down')}
                                                            disabled={
                                                                overrideLoading[p.username] !== undefined &&
                                                                overrideLoading[p.username] !== null
                                                            }
                                                            className="inline-flex items-center justify-center w-9 h-9 rounded-xl border bg-white/60 dark:bg-gray-900/20 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                                            style={{ borderColor: 'var(--card-border)' }}
                                                            title="Smanji level"
                                                        >
                                                            <i className="fa-solid fa-arrow-down text-red-500" />
                                                        </button>

                                                        <button
                                                            onClick={() => handleOverride(p.username, 'up')}
                                                            disabled={
                                                                overrideLoading[p.username] !== undefined &&
                                                                overrideLoading[p.username] !== null
                                                            }
                                                            className="inline-flex items-center justify-center w-9 h-9 rounded-xl border bg-white/60 dark:bg-gray-900/20 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                                            style={{ borderColor: 'var(--card-border)' }}
                                                            title="Povećaj level"
                                                        >
                                                            <i className="fa-solid fa-arrow-up text-emerald-600" />
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <span className="text-gray-400">—</span>
                                                )}
                                            </td>

                                        </tr>
                                    ))}
                                </tbody>
                            </table>

                        </div>
                    </div>
                )}


            </div>
        </main>
    );
}


