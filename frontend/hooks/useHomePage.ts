'use client';

import { useCallback, useEffect, useState } from 'react';
import { apiClient, Course } from '@/lib/api';
import { filterVisibleCourses, groupCoursesBySemester, sortSemesterKeys } from '@/lib/courseGrouping';
import { useAuthenticatedUser } from '@/hooks/useAuthenticatedUser';

type RouterLike = {
  push: (href: string) => void;
};

export function useHomePage(router: RouterLike) {
  const { user } = useAuthenticatedUser(router);
  const [courses, setCourses] = useState<Course[]>([]);
  const [hiddenCourseIds, setHiddenCourseIds] = useState<number[]>([]);
  const [hiddenTermKeys, setHiddenTermKeys] = useState<string[]>([]);
  const [hiddenPrefsLoaded, setHiddenPrefsLoaded] = useState(false);
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [creatingCourse, setCreatingCourse] = useState(false);
  const [newCourseName, setNewCourseName] = useState('');
  const [newCourseDescription, setNewCourseDescription] = useState('');
  const [newCourseTermYear, setNewCourseTermYear] = useState(new Date().getFullYear());
  const [newCourseTermNumber, setNewCourseTermNumber] = useState<1 | 2>(1);
  const [courseFormError, setCourseFormError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [courseTab, setCourseTab] = useState<'classes' | 'hidden'>('classes');
  const [viewMode, setViewMode] = useState<'semester' | 'mindmap'>('semester');
  const [expandedTerms, setExpandedTerms] = useState<Record<string, boolean>>({});
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [joinCode, setJoinCode] = useState('');

  const loadCourses = useCallback(async () => {
    setLoadingCourses(true);
    try {
      const response = await apiClient.getCourses();
      setCourses(response.courses || []);
    } catch (error) {
      console.error('Failed to load courses:', error);
      setCourses([]);
    } finally {
      setLoadingCourses(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      void loadCourses();
    }
  }, [loadCourses, user]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = localStorage.getItem('hidden_course_ids');
    if (stored) {
      try {
        setHiddenCourseIds(JSON.parse(stored));
      } catch {
        setHiddenCourseIds([]);
      }
    }
    setHiddenPrefsLoaded(true);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || !hiddenPrefsLoaded) return;
    localStorage.setItem('hidden_course_ids', JSON.stringify(hiddenCourseIds));
  }, [hiddenCourseIds, hiddenPrefsLoaded]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = localStorage.getItem('hidden_term_keys');
    if (stored) {
      try {
        setHiddenTermKeys(JSON.parse(stored));
      } catch {
        setHiddenTermKeys([]);
      }
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || !hiddenPrefsLoaded) return;
    localStorage.setItem('hidden_term_keys', JSON.stringify(hiddenTermKeys));
  }, [hiddenPrefsLoaded, hiddenTermKeys]);

  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible' && user) {
        void loadCourses();
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, [loadCourses, user]);

  const handleJoinCourse = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      const response = await apiClient.joinCourse(joinCode);
      setShowJoinModal(false);
      setJoinCode('');
      await loadCourses();
      router.push(`/courses/${response.course_id}`);
    } catch (error) {
      alert('Invalid join code or you are already in this course.');
    }
  };

  const resetCreateCourseForm = () => {
    setShowCreateModal(false);
    setCourseFormError(null);
    setNewCourseName('');
    setNewCourseDescription('');
    setNewCourseTermYear(new Date().getFullYear());
    setNewCourseTermNumber(1);
  };

  const handleCreateCourse = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newCourseName.trim()) {
      setCourseFormError('Course name is required.');
      return;
    }

    setCreatingCourse(true);
    setCourseFormError(null);
    try {
      const newCourse = await apiClient.createCourse({
        name: newCourseName.trim(),
        description: newCourseDescription.trim() || undefined,
        term_year: newCourseTermYear,
        term_number: newCourseTermNumber,
      });
      resetCreateCourseForm();
      await loadCourses();
      router.push(`/courses/${newCourse.id}`);
    } catch (error) {
      console.error('Failed to create course:', error);
      setCourseFormError('Failed to create course. Please try again.');
    } finally {
      setCreatingCourse(false);
    }
  };

  const handleLogout = () => {
    apiClient.logout();
    router.push('/auth/login');
  };

  const toggleHidden = (courseId: number) => {
    setHiddenCourseIds((prev) =>
      prev.includes(courseId) ? prev.filter((id) => id !== courseId) : [...prev, courseId]
    );
  };

  const toggleTerm = (termKey: string) => {
    setExpandedTerms((prev) => ({ ...prev, [termKey]: !prev[termKey] }));
  };

  const toggleHiddenTerm = (termKey: string) => {
    setHiddenTermKeys((prev) =>
      prev.includes(termKey) ? prev.filter((key) => key !== termKey) : [...prev, termKey]
    );
  };

  const visibleCourses = filterVisibleCourses(courses, hiddenCourseIds, hiddenTermKeys, courseTab);
  const semesterGroups = groupCoursesBySemester(visibleCourses);
  const sortedSemesterKeys = sortSemesterKeys(semesterGroups);

  return {
    courseFormError,
    courseTab,
    creatingCourse,
    expandedTerms,
    handleCreateCourse,
    handleJoinCourse,
    handleLogout,
    hiddenCourseIds,
    hiddenTermKeys,
    joinCode,
    loadingCourses,
    newCourseDescription,
    newCourseName,
    newCourseTermNumber,
    newCourseTermYear,
    resetCreateCourseForm,
    semesterGroups,
    setCourseTab,
    setJoinCode,
    setNewCourseDescription,
    setNewCourseName,
    setNewCourseTermNumber,
    setNewCourseTermYear,
    setShowCreateModal,
    setShowJoinModal,
    setViewMode,
    showCreateModal,
    showJoinModal,
    sortedSemesterKeys,
    toggleHidden,
    toggleHiddenTerm,
    toggleTerm,
    user,
    viewMode,
    visibleCourses,
  };
}
