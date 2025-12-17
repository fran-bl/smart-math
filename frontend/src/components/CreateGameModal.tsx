'use client';

import { api, ApiError } from '@/lib/api';
import { useEffect, useState } from 'react';
import { Spinner } from './ui';

interface Topic {
    id: string;
    name: string;
}

interface CreateGameModalProps {
    isOpen: boolean;
    onClose: () => void;
    onTopicSelected?: (topic: Topic) => void;
    classroomId?: string;
}

export function CreateGameModal({ isOpen, onClose, onTopicSelected, classroomId }: CreateGameModalProps) {
    const [topics, setTopics] = useState<Topic[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);

    // Fetch topics when modal opens
    useEffect(() => {
        if (isOpen) {
            fetchTopics();
        }
    }, [isOpen]);

    const fetchTopics = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const data = await api.get<Topic[]>('/topics/');
            setTopics(data);
        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError('Nije moguće učitati teme');
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleClose = () => {
        setSelectedTopic(null);
        setError(null);
        onClose();
    };

    const handleSelectTopic = (topic: Topic) => {
        setSelectedTopic(topic);
    };

    const handleConfirm = () => {
        if (selectedTopic && onTopicSelected) {
            onTopicSelected(selectedTopic);
        }
        handleClose();
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

                <h2 className="text-xl font-bold mb-2">Nova igra</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    Odaberi temu za igru
                </p>

                {/* Error */}
                {error && (
                    <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                        <p className="text-red-600 dark:text-red-400 text-sm">
                            {error}
                        </p>
                    </div>
                )}

                {/* Loading state */}
                {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                        <Spinner />
                    </div>
                ) : topics.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                        <p>Nema dostupnih tema</p>
                    </div>
                ) : (
                    <>
                        {/* Topics list */}
                        <div className="space-y-2 max-h-64 overflow-y-auto mb-4">
                            {topics.map((topic) => (
                                <button
                                    key={topic.id}
                                    onClick={() => handleSelectTopic(topic)}
                                    className={`w-full text-left px-4 py-3 rounded-xl border transition-all
                                        ${selectedTopic?.id === topic.id
                                            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                                            : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-gray-50 dark:hover:bg-gray-800'
                                        }`}
                                >
                                    <span className="font-medium">{topic.name}</span>
                                </button>
                            ))}
                        </div>

                        {/* Confirm button */}
                        <button
                            onClick={handleConfirm}
                            disabled={!selectedTopic}
                            className="btn btn-primary w-full py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {selectedTopic ? `Pokreni igru: ${selectedTopic.name}` : 'Odaberi temu'}
                        </button>
                    </>
                )}
            </div>
        </div>
    );
}

