'use client';

import { useAuthStore } from '@/lib/store';
import { useState } from 'react';
import { Spinner } from './ui';

interface RegisterModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function RegisterModal({ isOpen, onClose }: RegisterModalProps) {
    const { register, isLoading, error, clearError } = useAuthStore();

    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [success, setSuccess] = useState(false);
    const [validationError, setValidationError] = useState<string | null>(null);

    const displayError = validationError || error;

    const handleClose = () => {
        setSuccess(false);
        setUsername('');
        setPassword('');
        setValidationError(null);
        clearError();
        onClose();
    };

    const handleRegister = async () => {
        setValidationError(null);
        clearError();
        setSuccess(false);

        if (!username.trim()) {
            setValidationError('Molimo unesite korisničko ime');
            return;
        }

        if (!password.trim()) {
            setValidationError('Molimo unesite lozinku');
            return;
        }

        const result = await register(
            username.trim(),
            'teacher',
            password
        );

        if (result) {
            setSuccess(true);
            setUsername('');
            setPassword('');
            // Auto close after 2 seconds
            setTimeout(() => {
                handleClose();
            }, 1000);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="card p-6 max-w-sm w-full relative animate-in fade-in zoom-in duration-200">
                {/* Close button */}
                <button
                    onClick={handleClose}
                    className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                    ✕
                </button>

                <h2 className="text-xl font-bold mb-4">👨‍🏫 Registracija profesora</h2>

                {/* Success message */}
                {success ? (
                    <div className="text-center py-6">
                        <div className="text-4xl mb-3">✅</div>
                        <p className="text-green-600 dark:text-green-400 font-medium">
                            Uspješno registrirano!
                        </p>
                    </div>
                ) : (
                    <>
                        {/* Error in modal */}
                        {displayError && (
                            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                                <p className="text-red-600 dark:text-red-400 text-sm">
                                    ⚠️ {displayError}
                                </p>
                            </div>
                        )}

                        {/* Username */}
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2 text-gray-600 dark:text-gray-300">
                                Korisničko ime
                            </label>
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Unesite ime..."
                                disabled={isLoading}
                                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 
                                           bg-white dark:bg-gray-800 focus:border-indigo-500 dark:focus:border-indigo-400 
                                           outline-none transition-colors disabled:opacity-50"
                            />
                        </div>

                        {/* Password */}
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2 text-gray-600 dark:text-gray-300">
                                Lozinka
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Unesite lozinku..."
                                disabled={isLoading}
                                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 
                                           bg-white dark:bg-gray-800 focus:border-emerald-500 dark:focus:border-emerald-400 
                                           outline-none transition-colors disabled:opacity-50"
                            />
                        </div>

                        {/* Register button */}
                        <button
                            onClick={handleRegister}
                            disabled={isLoading}
                            className="btn btn-secondary w-full text-center py-2 disabled:opacity-70"
                        >
                            {isLoading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <Spinner />
                                    Registracija...
                                </span>
                            ) : (
                                'Registriraj se'
                            )}
                        </button>
                    </>
                )}
            </div>
        </div>
    );
}

