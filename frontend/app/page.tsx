'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient, Course, User } from '@/lib/api';
import Link from 'next/link';

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [creatingCourse, setCreatingCourse] = useState(false);
  const [newCourseName, setNewCourseName] = useState('');
  const [newCourseDescription, setNewCourseDescription] = useState('');
  const [courseFormError, setCourseFormError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  // States for Join Course feature
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [joinCode, setJoinCode] = useState('');

  useEffect(() => {
    if (!apiClient.isAuthenticated()) {
      router.push('/auth/login');
      return;
    }

    const storedUser = apiClient.getStoredUser();
    if (storedUser) {
      setUser(storedUser);
    } else {
      apiClient.getCurrentUser()
        .then(setUser)
        .catch(() => {
          apiClient.logout();
          router.push('/auth/login');
        });
    }
  }, [router]);

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
      loadCourses();
    }
  }, [user, loadCourses]);

  const handleJoinCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await apiClient.joinCourse(joinCode);
      setShowJoinModal(false);
      setJoinCode('');
      await loadCourses(); // Refresh the dashboard
      router.push(`/courses/${response.course_id}`);
    } catch (error) {
      alert("Invalid join code or you are already in this course.");
    }
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
      });
      setNewCourseName('');
      setNewCourseDescription('');
      setShowCreateModal(false);
      await loadCourses();
      router.push(`/courses/${newCourse.id}`);
    } catch (error) {
      console.error('Failed to create course:', error);
      setCourseFormError('Failed to create course. Please try again.');
    } finally {
      setCreatingCourse(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
  };

  // Course Card Component
  function CourseCard({ course, createdDate }: { course: Course; createdDate: string }) {
    const [healthStatus, setHealthStatus] = useState<'high' | 'healthy' | 'new' | null>(null);
    const [loadingHealth, setLoadingHealth] = useState(true);

    useEffect(() => {
      if (user?.role === 'instructor') {
        loadHealthStatus();
      } else {
        setLoadingHealth(false);
      }
    }, [course.id, user?.role]);

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

    const handleDelete = async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      
      if (window.confirm(`Permanently delete "${course.name}"?`)) {
        try {
          await apiClient.deleteCourse(course.id);
          window.location.href = "/"; 
        } catch (error) {
          console.error("Delete failed:", error);
          alert("Could not delete. If the page hangs, restart the backend server.");
        }
      }
    };

    return (
      <Link
        href={`/courses/${course.id}`}
        className="flex-shrink-0 w-80 h-96 bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow cursor-pointer group relative"
      >
        {/* Delete Button */}
        {user?.role === 'instructor' && (
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

        {/* Health Badge */}
        {user?.role === 'instructor' && !loadingHealth && healthStatus && (
          <div className="absolute top-4 left-4 z-10">
            {healthStatus === 'high' && (
              <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full border border-red-200">
                ⚠️ High confusion
              </span>
            )}
            {healthStatus === 'healthy' && (
              <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full border border-green-200">
                🟢 Healthy
              </span>
            )}
            {healthStatus === 'new' && (
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full border border-blue-200">
                New activity
              </span>
            )}
          </div>
        )}

        {/* Course Card Header */}
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

        {/* Course Card Content */}
        <div className="p-6 h-64 flex flex-col">
          <div className="flex-1">
            <h3 className="text-xl font-semibold text-gray-900 mb-2 line-clamp-2 group-hover:text-primary-600 transition-colors">
              {course.name}
            </h3>
            
            {/* Show Join Code to Instructors */}
            {user?.role === 'instructor' && (
              <div className="mb-2 flex items-center space-x-1">
                <span className="text-[10px] uppercase font-bold text-gray-400">Join Code:</span>
                <code className="text-xs font-mono font-bold bg-gray-50 text-primary-700 px-1.5 py-0.5 rounded border border-gray-200">
                  {course.join_code}
                </code>
              </div>
            )}

            {course.description && (
              <p className="text-sm text-gray-500 mb-4 line-clamp-2">
                {course.description}
              </p>
            )}
            <div className="flex items-center text-xs text-gray-400 space-x-2">
              <span>{createdDate}</span>
              <span>•</span>
              <span>{course.lecture_count} {course.lecture_count === 1 ? 'lecture' : 'lectures'}</span>
            </div>
          </div>
          <div className="mt-auto pt-4 border-t border-gray-100">
            <div className="flex items-center text-sm text-primary-600 font-medium">
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

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">L</span>
              </div>
              <h1 className="text-2xl font-bold text-gray-900">LectureSense</h1>
            </div>
            <nav className="flex items-center space-x-4">
              {user?.role === 'instructor' && (
                <Link
                  href="/instructor"
                  className="text-sm font-medium text-gray-700 hover:text-primary-600"
                >
                  Analytics
                </Link>
              )}
              {user && (
                <div className="flex items-center space-x-3 border-l border-gray-300 pl-4">
                  <div className="flex flex-col items-end">
                    <span className="text-sm font-medium text-gray-900">{user.email}</span>
                    <span className="text-xs text-gray-500 capitalize">{user.role}</span>
                  </div>
                  <button
                    onClick={() => {
                      apiClient.logout();
                      router.push('/auth/login');
                    }}
                    className="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md transition-colors"
                  >
                    Logout
                  </button>
                </div>
              )}
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Your Courses</h2>
          <p className="text-gray-600">
            Select a course to view lectures, ask questions, and access study materials.
          </p>
        </div>

        {loadingCourses ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <svg className="w-8 h-8 animate-spin mx-auto text-primary-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p className="mt-4 text-gray-500">Loading courses...</p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto pb-6 -mx-4 px-4">
            <div className="flex space-x-4 min-w-max">
              {/* Create New Course Card */}
              {user?.role === 'instructor' && (
                <div
                  onClick={() => setShowCreateModal(true)}
                  className="flex-shrink-0 w-80 h-96 bg-gray-100 border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-primary-400 hover:bg-gray-50 transition-colors"
                >
                  <div className="w-16 h-16 bg-gray-300 rounded-full flex items-center justify-center mb-4">
                    <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-gray-700">Create new course</p>
                </div>
              )}

              {/* Join Course Card (Visible to students and instructors) */}
              <div
                onClick={() => setShowJoinModal(true)}
                className="flex-shrink-0 w-80 h-96 bg-blue-50 border-2 border-dashed border-blue-300 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-blue-400 hover:bg-blue-100 transition-colors"
              >
                <div className="w-16 h-16 bg-blue-200 rounded-full flex items-center justify-center mb-4">
                  <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                </div>
                <p className="text-lg font-medium text-blue-700">Join course with code</p>
              </div>

              {courses.map((course) => (
                <CourseCard key={course.id} course={course} createdDate={formatDate(course.created_at)} />
              ))}
            </div>
          </div>
        )}

        {!loadingCourses && courses.length === 0 && user?.role !== 'instructor' && (
          <div className="text-center py-20">
            <p className="text-gray-500">No courses available. Use a join code to get started.</p>
          </div>
        )}

        {!loadingCourses && courses.length === 0 && user?.role === 'instructor' && (
          <div className="text-center py-20">
            <p className="text-gray-500 mb-4">You haven't created any courses yet.</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
            >
              Create Your First Course
            </button>
          </div>
        )}
      </main>

      {/* Create Course Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-gray-900">Create New Course</h3>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setCourseFormError(null);
                  setNewCourseName('');
                  setNewCourseDescription('');
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <form onSubmit={handleCreateCourse} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Course Name</label>
                  <input
                    type="text"
                    value={newCourseName}
                    onChange={(e) => setNewCourseName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="e.g. CS101 - Algorithms"
                    required
                  autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={newCourseDescription}
                    onChange={(e) => setNewCourseDescription(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                    placeholder="Optional course description"
                  />
                </div>
                {courseFormError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
                    {courseFormError}
                  </div>
                )}
              <div className="flex space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setCourseFormError(null);
                    setNewCourseName('');
                    setNewCourseDescription('');
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingCourse}
                  className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {creatingCourse ? 'Creating...' : 'Create'}
                </button>
                    </div>
                  </form>
          </div>
        </div>
      )}

      {/* Join Course Modal */}
      {showJoinModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Join a Course</h3>
            <form onSubmit={handleJoinCourse} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Enter Join Code</label>
                <input
                  type="text"
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-center font-mono text-xl tracking-widest uppercase"
                  placeholder="XXXXXX"
                  maxLength={6}
                  required
                  autoFocus
                />
              </div>
              <div className="flex space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowJoinModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
                >
                  Join
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}