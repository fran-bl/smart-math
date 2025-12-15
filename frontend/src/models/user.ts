export type UserRole = 'student' | 'teacher';

export interface User {
    id: string;
    username: string;
    role: UserRole;
    createdAt?: string;
}

export interface StudentUser extends User {
    role: 'student';
    classroomId?: string;
    stats?: {
        quizzesCompleted: number;
        averageScore: number;
    };
}

export interface TeacherUser extends User {
    role: 'teacher';
    classrooms?: string[];
}

