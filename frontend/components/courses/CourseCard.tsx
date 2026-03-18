'use client';

/**
 * This component renders course-related UI for course card.
 * It keeps course screens modular by isolating one focused piece of the interface.
 */
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { apiClient, Course, User } from '@/lib/api';

type CourseCardProps = {
  course: Course;
  createdDate: string;
  isHidden: boolean;
  onToggleHidden: (courseId: number) => void;
  userRole?: User['role'];
};

export default function CourseCard({
  course,
  createdDate,
  isHidden,
  onToggleHidden,
  userRole,
}: CourseCardProps) {
  const [healthStatus, setHealthStatus] = useState<'high' | 'healthy' | 'new' | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);

  useEffect(() => {
    const loadHealthStatus = async () => {
      try {
        const analytics = await apiClient.getCourseAnalytics(course.id);
        if (analytics.trend_direction === 'up' && analytics.trend_percentage > 15) {
          setHealthStatus('high');
        } else if (analytics.total_questions === 0) {
          setHealthStatus('new');
        } else {
          setHealthStatus('healthy');
        }
      } catch (error) {
        setHealthStatus('new');
      } finally {
        setLoadingHealth(false);
      }
    };

    if (userRole === 'instructor') {
      void loadHealthStatus();
    } else {
      setLoadingHealth(false);
    }
  }, [course.id, userRole]);

  const handleDelete = async (event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();

    if (!window.confirm(`Permanently delete "${course.name}"?`)) {
      return;
    }

    try {
      await apiClient.deleteCourse(course.id);
      window.location.href = '/';
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Could not delete. If the page hangs, restart the backend server.');
    }
  };

  return (
    <Link
      href={`/courses/${course.id}`}
      className="flex-shrink-0 w-80 h-96 bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow cursor-pointer group relative"
    >
      {userRole === 'instructor' && (
        <button
          onClick={handleDelete}
          className="absolute top-2 right-2 z-30 p-2 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-md hover:bg-red-600 focus:outline-none"
          title="Delete Course"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      )}

      <button
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onToggleHidden(course.id);
        }}
        className="absolute top-2 left-2 z-30 px-2 py-1 bg-white text-xs text-gray-700 rounded-full border border-gray-200 opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
        title={isHidden ? 'Unhide Course' : 'Hide Course'}
      >
        {isHidden ? 'Unhide' : 'Hide'}
      </button>

      {userRole === 'instructor' && !loadingHealth && healthStatus && (
        <div className="absolute top-4 left-4 z-10">
          {healthStatus === 'high' && (
            <span className="px-2 py-1 bg-red-100 text-red-700 text-sm font-medium rounded-full border border-red-200">
              High activity
            </span>
          )}
          {healthStatus === 'healthy' && (
            <span className="px-2 py-1 bg-green-100 text-green-700 text-sm font-medium rounded-full border border-green-200">
              Healthy
            </span>
          )}
          {healthStatus === 'new' && (
            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-sm font-medium rounded-full border border-blue-200">
              New activity
            </span>
          )}
        </div>
      )}

      <div className="h-32 bg-gradient-to-br from-primary-500 to-primary-700 relative overflow-hidden">
        <div className="absolute inset-0 bg-black opacity-10"></div>
        <div className="absolute bottom-4 left-4 group-hover:opacity-0 transition-opacity">
          <div className="w-10 h-10 bg-white bg-opacity-20 rounded-lg flex items-center justify-center backdrop-blur-sm">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
        </div>
      </div>

      <div className="p-6 h-64 flex flex-col">
        <div className="flex-1">
          <h3 className="text-3xl font-semibold text-gray-900 mb-2 line-clamp-2 group-hover:text-primary-600 transition-colors">
            {course.name}
          </h3>

          {userRole === 'instructor' && course.join_code && (
            <div className="mb-2 flex items-center space-x-2">
              <span className="text-sm uppercase font-bold text-gray-400">Join Code:</span>
              <code className="text-base font-mono font-bold bg-gray-50 text-primary-700 px-2 py-0.5 rounded border border-gray-200">
                {course.join_code}
              </code>
              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  void navigator.clipboard.writeText(course.join_code || '');
                }}
                className="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-primary-600"
                title="Copy join code"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
          )}

          {course.description && <p className="text-base text-gray-600 mb-4 line-clamp-2">{course.description}</p>}

          <div className="flex items-center text-base text-gray-500 space-x-2">
            <span>{createdDate}</span>
            <span>•</span>
            <span>{course.lecture_count} {course.lecture_count === 1 ? 'lecture' : 'lectures'}</span>
          </div>
        </div>

        <div className="mt-auto pt-4 border-t border-gray-100">
          <div className="flex items-center text-lg text-primary-600 font-medium">
            <span>Open course</span>
            <svg className="w-4 h-4 ml-2 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
      </div>
    </Link>
  );
}
