'use client';

import { io, Socket } from 'socket.io-client';

const SOCKET_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let socket: Socket | null = null;
let socketToken: string | null = null;

export function getAuthedSocket(token: string): Socket {
    const cleanToken = token.trim();
    if (socket && socketToken === cleanToken) return socket;

    if (socket) {
        socket.disconnect();
        socket = null;
        socketToken = null;
    }

    socketToken = cleanToken;
    socket = io(SOCKET_URL, {
        transports: ['polling', 'websocket'],
        withCredentials: true,
        auth: { token: cleanToken },
        extraHeaders: { Authorization: `Bearer ${cleanToken}` },
    });

    return socket;
}

export function disconnectSocket() {
    if (socket) {
        socket.disconnect();
        socket = null;
        socketToken = null;
    }
}


