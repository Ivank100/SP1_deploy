'use client';

/**
 * This hook manages state and actions for the course page workflow.
 * It loads data, tracks UI state, and returns handlers used by page components.
 */
import { useCallback, useEffect, useState } from 'react';
import { apiClient, Course } from '@/lib/api';
import { useAuthenticatedUser } from '@/hooks/useAuthenticatedUser';

type RouterLike = {
  push: (href: string) => void;
};

export function useCoursePage(courseId: number, router: RouterLike) {
  const { user } = useAuthenticatedUser(router);
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadCourse = useCallback(async () => {
    try {
      const coursesResponse = await apiClient.getCourses();
      const foundCourse = coursesResponse.courses.find((item) => item.id === courseId);
      if (!foundCourse) {
        router.push('/');
        return;
      }

      setCourse(foundCourse);
    } catch (error) {
      console.error('Failed to load course:', error);
      router.push('/');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [courseId, router]);

  useEffect(() => {
    if (user && courseId) {
      void loadCourse();
    }
  }, [courseId, loadCourse, user]);

  return {
    course,
    loadCourse,
    loading,
    refreshing,
    setRefreshing,
    user,
  };
}
