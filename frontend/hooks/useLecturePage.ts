'use client';

import { useCallback, useEffect, useState } from 'react';
import { apiClient, Lecture, User } from '@/lib/api';

type RouterLike = {
  push: (href: string) => void;
};

export function useLecturePage(lectureId: number, router: RouterLike) {
  const [lecture, setLecture] = useState<Lecture | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [courseName, setCourseName] = useState<string | null>(null);

  const loadLecture = useCallback(async () => {
    try {
      const data = await apiClient.getLecture(lectureId);
      setLecture(data);

      if (data.course_id) {
        const courses = await apiClient.getCourses();
        const matched = courses.courses.find((course) => course.id === data.course_id);
        setCourseName(matched?.name || null);
      } else {
        setCourseName(null);
      }
    } catch (error) {
      console.error('Failed to load lecture:', error);
      router.push('/');
    } finally {
      setLoading(false);
    }
  }, [lectureId, router]);

  useEffect(() => {
    if (!apiClient.isAuthenticated()) {
      router.push('/auth/login');
      return;
    }

    const storedUser = apiClient.getStoredUser();
    if (storedUser) {
      setCurrentUser(storedUser);
    }

    void loadLecture();
  }, [loadLecture, router]);

  return {
    courseName,
    currentUser,
    lecture,
    loadLecture,
    loading,
    setLecture,
  };
}
