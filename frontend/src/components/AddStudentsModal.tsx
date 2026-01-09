'use client';

import { api, ApiError } from '@/lib/api';
import { useEffect, useMemo, useState } from 'react';
import { Spinner } from './ui';

interface AddStudentsModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess?: () => void;
    classroomName: string;
}

interface UnassignedStudent {
    id: string;
    username: string;
}

export function AddStudentsModal({ isOpen, onClose, onSuccess, classroomName }: AddStudentsModalProps) {
    const [isLoading, setIsLoading] = useState(false);
    const [isLoadingStudents, setIsLoadingStudents] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const [addedCount, setAddedCount] = useState(0);

    const [availableStudents, setAvailableStudents] = useState<UnassignedStudent[]>([]);
    const [selectedUsernames, setSelectedUsernames] = useState<string[]>([]);

    const selectedSet = useMemo(() => new Set(selectedUsernames), [selectedUsernames]);

    useEffect(() => {
        if (!isOpen) return;

        const fetchUnassigned = async () => {
            setIsLoadingStudents(true);
            setError(null);
            try {
                const data = await api.get<UnassignedStudent[]>('/classroom/unassigned-students');
                setAvailableStudents(data);
                setSelectedUsernames([]);
            } catch (err) {
                if (err instanceof ApiError) {
                    setError(err.message);
                } else {
                    setError('Nije moguće učitati učenike');
                }
            } finally {
                setIsLoadingStudents(false);
            }
        };

        fetchUnassigned();
    }, [isOpen]);

    const handleClose = () => {
        setAvailableStudents([]);
        setSelectedUsernames([]);
        setError(null);
        setSuccess(false);
        setAddedCount(0);
        onClose();
    };

    const handleSubmit = async () => {
        setError(null);

        if (selectedUsernames.length === 0) {
            setError('Molimo odaberite barem jednog učenika');
            return;
        }

        setIsLoading(true);

        try {
            await api.post('/classroom/add-students', {
                classroom_name: classroomName,
                student_list: selectedUsernames,
            });

            setAddedCount(selectedUsernames.length);
            setSuccess(true);
            setSelectedUsernames([]);

            setTimeout(() => {
                handleClose();
                onSuccess?.();
            }, 1500);
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

    const toggleSelected = (username: string) => {
        setSelectedUsernames(prev => (
            prev.includes(username)
                ? prev.filter(u => u !== username)
                : [...prev, username]
        ));
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="card p-6 max-w-md w-full relative animate-in fade-in zoom-in duration-200">
                {/* Close button */}
                <button
                    onClick={handleClose}
                    className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                    ✕
                </button>

                <h2 className="text-xl font-bold mb-1">Dodaj učenike</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    Razred: <span className="font-medium">{classroomName}</span>
                </p>

                {/* Success message */}
                {success ? (
                    <div className="text-center py-6">
                        <p className="text-green-600 dark:text-green-400 font-medium">
                            Dodano {addedCount} učenika!
                        </p>
                    </div>
                ) : (
                    <>
                        {/* Error */}
                        {error && (
                            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                                <p className="text-red-600 dark:text-red-400 text-sm">
                                    {error}
                                </p>
                            </div>
                        )}

                        {/* Unassigned students list */}
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2 text-gray-600 dark:text-gray-300">
                                Odaberi učenike (samo oni bez razreda)
                            </label>

                            {isLoadingStudents ? (
                                <div className="flex items-center gap-2 text-gray-500 py-3">
                                    <Spinner />
                                    <span>Učitavanje učenika...</span>
                                </div>
                            ) : availableStudents.length === 0 ? (
                                <div className="text-sm text-gray-500 py-2">
                                    Nema dostupnih učenika bez razreda.
                                </div>
                            ) : (
                                <div className="max-h-56 overflow-y-auto rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                                    {availableStudents.map((s) => {
                                        const checked = selectedSet.has(s.username);
                                        return (
                                            <label
                                                key={s.id}
                                                className="flex items-center gap-3 px-3 py-2 border-b last:border-b-0 border-gray-100 dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/40"
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={checked}
                                                    onChange={() => toggleSelected(s.username)}
                                                    disabled={isLoading}
                                                    className="checkbox checkbox-sm"
                                                />
                                                <span className="text-sm font-medium">{s.username}</span>
                                            </label>
                                        );
                                    })}
                                </div>
                            )}

                            {selectedUsernames.length > 0 && (
                                <div className="mt-2 text-xs text-gray-400">
                                    Odabrano: {selectedUsernames.length}
                                </div>
                            )}
                        </div>

                        {/* Submit button */}
                        <button
                            onClick={handleSubmit}
                            disabled={isLoading || isLoadingStudents || availableStudents.length === 0}
                            className="btn btn-primary w-full text-center py-2 disabled:opacity-70"
                        >
                            {isLoading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <Spinner />
                                    Dodavanje...
                                </span>
                            ) : (
                                'Dodaj učenike'
                            )}
                        </button>
                    </>
                )}
            </div>
        </div>
    );
}

