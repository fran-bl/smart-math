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

    const [players, setPlayers] = useState<string[]>([]);
    const [playersDetailed, setPlayersDetailed] = useState<
        Array<{ user_id: string; username: string; level: number; xp: number; rank: number }>
    >([]);
    const [isConnecting, setIsConnecting] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [hasStarted] = useState(true);
    const socketRef = useRef<Socket | null>(null);

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


    if (!isHydrated || !isAuthenticated || !user || user.role !== 'teacher') {
        return (
            <main className="min-h-screen flex items-center justify-center">
                <Spinner />
            </main>
        );
    }

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
                    <button
                        onClick={() => router.push('/teacher/dashboard')}
                        className="btn btn-outline !py-2 !px-4"
                    >
                        Natrag
                    </button>
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


