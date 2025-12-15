// Letter -> Emoji mapping
export const EMOJI_MAP: Record<string, string> = {
    A: '🌟',
    B: '🐶',
    C: '🌈',
    D: '🍎',
    E: '⚽',
};

export const PASSWORD_KEYS = Object.keys(EMOJI_MAP);

export const getEmoji = (letter: string): string => EMOJI_MAP[letter] || '';

export const getLetter = (emoji: string): string => {
    const entry = Object.entries(EMOJI_MAP).find(([, e]) => e === emoji);
    return entry ? entry[0] : '';
};

export const passwordToEmojis = (password: string[]): string => {
    return password.map(getEmoji).join('');
};

export const isValidPassword = (password: string[]): boolean => {
    return password.every(p => p === '' || PASSWORD_KEYS.includes(p));
};
