'use client';

import { api, ApiError } from '@/lib/api';
import { passwordToEmojis } from '@/lib/utils';
import { useState } from 'react';
import { Spinner } from './ui';

interface CreateClassroomModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess?: () => void;
}

interface CreateClassroomResponse {
    message: string;
    classroom_code: string;
}

export function CreateClassroomModal({ isOpen, onClose, onSuccess }: CreateClassroomModalProps) {
    const [classroomName, setClassroomName] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const [generatedCode, setGeneratedCode] = useState<string | null>(null);

    const handleClose = () => {
        setClassroomName('');
        setError(null);
        setSuccess(false);
        setGeneratedCode(null);
        onClose();
    };

    const handleCreate = async () => {
        setError(null);

        if (!classroomName.trim()) {
            setError('Molimo unesite naziv razreda');
            return;
        }

        setIsLoading(true);

        try {
            const response = await api.post<CreateClassroomResponse>('/classroom/create', {
                classroom_name: classroomName.trim(),
            });

            setGeneratedCode(response.classroom_code);
            setSuccess(true);
            onSuccess?.();
        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError('Došlo je do greške');
            }
        } finally {
            setIsLoading(false);
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

                <h2 className="text-xl font-bold mb-4">📚 Novi razred</h2>

                {/* Success message */}
                {success ? (
                    <div className="text-center py-6">
                        <div className="text-4xl mb-3">✅</div>
                        <p className="text-green-600 dark:text-green-400 font-medium mb-4">
                            Razred uspješno kreiran!
                        </p>
                        {generatedCode && (
                            <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 mb-4">
                                <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                                    Šifra razreda:
                                </p>
                                <p className="text-4xl tracking-widest mb-2">
                                    {passwordToEmojis(generatedCode.split(''))}
                                </p>
                            </div>
                        )}
                        <button
                            onClick={handleClose}
                            className="btn btn-secondary w-full text-center py-2"
                        >
                            U redu
                        </button>
                    </div>
                ) : (
                    <>
                        {/* Error */}
                        {error && (
                            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                                <p className="text-red-600 dark:text-red-400 text-sm">
                                    ⚠️ {error}
                                </p>
                            </div>
                        )}

                        {/* Classroom name */}
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2 text-gray-600 dark:text-gray-300">
                                Naziv razreda
                            </label>
                            <input
                                type="text"
                                value={classroomName}
                                onChange={(e) => setClassroomName(e.target.value)}
                                placeholder="Naziv razreda..."
                                disabled={isLoading}
                                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 
                                           bg-white dark:bg-gray-800 focus:border-emerald-500 dark:focus:border-emerald-400 
                                           outline-none transition-colors disabled:opacity-50"
                            />
                            <p className="text-xs text-gray-400 mt-1">
                                Šifra razreda će se automatski generirati
                            </p>
                        </div>

                        {/* Create button */}
                        <button
                            onClick={handleCreate}
                            disabled={isLoading}
                            className="btn btn-secondary w-full text-center py-2 disabled:opacity-70"
                        >
                            {isLoading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <Spinner />
                                    Kreiranje...
                                </span>
                            ) : (
                                '+ Kreiraj razred'
                            )}
                        </button>
                    </>
                )}
            </div>
        </div>
    );
}
