'use client';

import { useEffect, useState } from 'react';
import { apiClient, Course, Lecture, LectureHealthResponse, QueryListResponse } from '@/lib/api';
import { useAuthenticatedUser } from '@/hooks/useAuthenticatedUser';

type RouterLike = {
  push: (href: string) => void;
};

export function useInstructorDashboardPage(router: RouterLike) {
  const { user } = useAuthenticatedUser(router);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [selectedLectureId, setSelectedLectureId] = useState<number | null>(null);
  const [health, setHealth] = useState<LectureHealthResponse | null>(null);
  const [queries, setQueries] = useState<QueryListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'queries'>('overview');
  const [showAllRecurringTopics, setShowAllRecurringTopics] = useState(false);

  useEffect(() => {
    if (user) {
      void loadCourses();
    }
  }, [user]);

  useEffect(() => {
    if (selectedCourseId) {
      void loadLectures();
    } else {
      setLectures([]);
      setSelectedLectureId(null);
    }
  }, [selectedCourseId]);

  useEffect(() => {
    void loadData();
  }, [selectedCourseId, selectedLectureId]);

  const loadCourses = async () => {
    try {
      const coursesData = await apiClient.getCourses();
      setCourses(coursesData.courses);
    } catch (error) {
      console.error('Failed to load courses:', error);
    }
  };

  const loadLectures = async () => {
    if (!selectedCourseId) {
      setLectures([]);
      setSelectedLectureId(null);
      return;
    }

    try {
      const lecturesData = await apiClient.getLectures(selectedCourseId);
      setLectures(lecturesData.lectures.filter((lecture) => lecture.status === 'completed'));
      setSelectedLectureId(null);
    } catch (error) {
      console.error('Failed to load lectures:', error);
      setLectures([]);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const lectureIdParam = selectedLectureId ?? undefined;
      const courseIdParam = selectedCourseId ?? undefined;

      const [healthData, queriesData] = await Promise.all([
        apiClient.getLectureHealth(courseIdParam, lectureIdParam),
        apiClient.getAllQueries(1000, lectureIdParam, courseIdParam),
      ]);

      setHealth(healthData);
      setQueries(queriesData);
    } catch (error) {
      console.error('Failed to load analytics:', error);
      setHealth({ lectures: [], total_lectures: 0 });
      setQueries({ queries: [], total: 0 });
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    apiClient.logout();
    router.push('/auth/login');
  };

  const queriesList = queries?.queries ?? [];
  const totalQuestions = Math.max(queries?.total ?? 0, queriesList.length);
  const now = new Date();
  const sevenDaysAgo = new Date(now);
  sevenDaysAgo.setDate(now.getDate() - 7);
  const activeStudentsLast7Days = new Set(
    queriesList
      .filter((query) => query.created_at && new Date(query.created_at) >= sevenDaysAgo)
      .map((query) => query.user_email || query.user_id?.toString())
      .filter(Boolean)
  ).size;

  const mostConfusingLecture = health?.lectures?.length
    ? [...health.lectures].sort((a, b) => b.query_count - a.query_count)[0]
    : null;

  const topLecturesByConfusion = health?.lectures?.length
    ? [...health.lectures].sort((a, b) => b.query_count - a.query_count).slice(0, 5)
    : [];

  const topStudents = (() => {
    const counts = new Map<string, number>();
    queriesList.forEach((query) => {
      const key = query.user_email || query.user_id?.toString();
      if (!key) return;
      counts.set(key, (counts.get(key) || 0) + 1);
    });
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5);
  })();

  const lecturesWithQuestions = health?.lectures?.filter((lecture) => lecture.query_count > 0).length ?? 0;

  return {
    activeStudentsLast7Days,
    activeTab,
    courses,
    handleLogout,
    health,
    lectures,
    lecturesWithQuestions,
    loading,
    mostConfusingLecture,
    queries,
    queriesList,
    selectedCourseId,
    selectedLectureId,
    setActiveTab,
    setSelectedCourseId,
    setSelectedLectureId,
    setShowAllRecurringTopics,
    showAllRecurringTopics,
    topLecturesByConfusion,
    topStudents,
    totalQuestions,
    user,
  };
}
