'use client';

import { useCallback, useEffect, useState } from 'react';
import { apiClient, Course, User } from '@/lib/api';

type RouterLike = {
  push: (href: string) => void;
};

export function useCoursePage(courseId: number, router: RouterLike) {
  const [user, setUser] = useState<User | null>(null);
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
    if (!apiClient.isAuthenticated()) {
      router.push('/auth/login');
      return;
    }

    const storedUser = apiClient.getStoredUser();
    if (storedUser) {
      setUser(storedUser);
      return;
    }

    apiClient
      .getCurrentUser()
      .then(setUser)
      .catch(() => {
        apiClient.logout();
        router.push('/auth/login');
      });
  }, [router]);

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
