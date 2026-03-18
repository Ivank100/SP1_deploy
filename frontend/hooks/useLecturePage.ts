'use client';

import { useCallback, useEffect, useState } from 'react';
import { apiClient, Lecture } from '@/lib/api';
import { useAuthenticatedUser } from '@/hooks/useAuthenticatedUser';

type RouterLike = {
  push: (href: string) => void;
};

export function useLecturePage(lectureId: number, router: RouterLike) {
  const { user: currentUser } = useAuthenticatedUser(router);
  const [lecture, setLecture] = useState<Lecture | null>(null);
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
    if (apiClient.isAuthenticated()) {
      void loadLecture();
    }
  }, [loadLecture]);

  return {
    courseName,
    currentUser,
    lecture,
    loadLecture,
    loading,
    setLecture,
  };
}
