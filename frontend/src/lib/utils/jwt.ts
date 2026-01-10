export type JwtPayload = Record<string, unknown> & {
    exp?: number | string;
};

function base64UrlDecodeToString(input: string): string {
    const b64 = input.replace(/-/g, '+').replace(/_/g, '/');
    const pad = b64.length % 4 ? '='.repeat(4 - (b64.length % 4)) : '';
    const normalized = b64 + pad;

    // Browser
    if (typeof globalThis !== 'undefined' && typeof (globalThis as any).atob === 'function') {
        return (globalThis as any).atob(normalized);
    }

    // Node
    const buf = (globalThis as any).Buffer?.from?.(normalized, 'base64');
    if (buf) return buf.toString('utf-8');

    throw new Error('No base64 decoder available');
}

export function decodeJwtPayload(token: string): JwtPayload | null {
    try {
        const parts = token.split('.');
        if (parts.length < 2) return null;
        const json = base64UrlDecodeToString(parts[1]);
        const payload = JSON.parse(json) as JwtPayload;
        return payload;
    } catch {
        return null;
    }
}

// token expiry timestamp
export function getJwtExpiryMs(token: string): number | null {
    const payload = decodeJwtPayload(token);
    const exp = payload?.exp;
    if (!exp) return null;

    if (typeof exp === 'number' && Number.isFinite(exp)) {
        return exp > 10_000_000_000 ? exp : exp * 1000;
    }

    if (typeof exp === 'string') {
        const asNumber = Number(exp);
        if (Number.isFinite(asNumber)) {
            return asNumber > 10_000_000_000 ? asNumber : asNumber * 1000;
        }
        const d = new Date(exp);
        const ms = d.getTime();
        return Number.isFinite(ms) ? ms : null;
    }

    return null;
}

export function isJwtExpired(token: string, skewMs: number = 5000): boolean {
    const expMs = getJwtExpiryMs(token);
    if (!expMs) return false;
    return Date.now() >= expMs - skewMs;
}


