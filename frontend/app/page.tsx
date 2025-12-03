'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient, Course, QueryResponse, CitationSource, User } from '@/lib/api';
import FileUpload from '@/components/FileUpload';
import LectureList from '@/components/LectureList';
import Link from 'next/link';

const formatTimestamp = (seconds?: number | null) => {
  if (seconds == null) return null;
  const total = Math.max(Math.floor(seconds), 0);
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  const hours = Math.floor(mins / 60);
  const minutes = mins % 60;
  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs
      .toString()
      .padStart(2, '0')}`;
  }
  return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

const describeSource = (source: CitationSource) => {
  if (source.page_number != null) {
    const isSlide = source.file_type === 'slides';
    const label = isSlide ? 'slide' : 'page';
    return `${label} ${source.page_number}`;
  }
  const start = formatTimestamp(source.timestamp_start ?? undefined);
  const end = formatTimestamp(source.timestamp_end ?? undefined);
  if (start && end && end !== start) {
    return `${start}-${end}`;
  }
  if (start) {
    return start;
  }
  return '';
};

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [creatingCourse, setCreatingCourse] = useState(false);
  const [newCourseName, setNewCourseName] = useState('');
  const [newCourseDescription, setNewCourseDescription] = useState('');
  const [courseQuestion, setCourseQuestion] = useState('');
  const [courseAsking, setCourseAsking] = useState(false);
  const [courseAnswer, setCourseAnswer] = useState<QueryResponse | null>(null);
  const [courseFormError, setCourseFormError] = useState<string | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);

  useEffect(() => {
    // Check authentication
    if (!apiClient.isAuthenticated()) {
      router.push('/auth/login');
      return;
    }

    // Load user info
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
    try {
      const response = await apiClient.getCourses();
      setCourses(response.courses);

      if (response.courses.length === 0) {
        setSelectedCourseId(null);
      } else if (!selectedCourseId || !response.courses.find(c => c.id === selectedCourseId)) {
        setSelectedCourseId(response.courses[0].id);
      }
    } catch (error) {
      console.error('Failed to load courses:', error);
    } finally {
      setLoadingCourses(false);
      setRefreshing(false);
    }
  }, [selectedCourseId]);

  useEffect(() => {
    if (user) {
      loadCourses();
    }
  }, [loadCourses, user]);

  useEffect(() => {
    const interval = setInterval(() => {
      const hasProcessing = courses.some(course =>
        course.lectures.some(lecture => lecture.status === 'processing')
      );
      if (hasProcessing) {
        loadCourses();
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [courses, loadCourses]);

  const selectedCourse = courses.find(course => course.id === selectedCourseId) || null;
  const selectedLectures = selectedCourse?.lectures ?? [];

  const handleUploadSuccess = () => {
    setRefreshing(true);
    loadCourses();
  };

  const handleDelete = async (id: number) => {
    try {
      await apiClient.deleteLecture(id);
      await loadCourses();
    } catch (error) {
      console.error('Failed to delete lecture:', error);
      alert('Failed to delete lecture');
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
      await apiClient.createCourse({
        name: newCourseName.trim(),
        description: newCourseDescription.trim() || undefined,
      });
      setNewCourseName('');
      setNewCourseDescription('');
      await loadCourses();
    } catch (error) {
      console.error('Failed to create course:', error);
      setCourseFormError('Failed to create course. Please try again.');
    } finally {
      setCreatingCourse(false);
    }
  };

  const handleCourseQuery = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedCourse || !courseQuestion.trim()) {
      return;
    }
    setCourseAsking(true);
    setQueryError(null);
    setCourseAnswer(null);
    try {
      const response = await apiClient.queryCourse(selectedCourse.id, courseQuestion);
      setCourseAnswer(response);
      setCourseQuestion('');
    } catch (error: any) {
      console.error('Failed to query course:', error);
      setQueryError(error.response?.data?.detail || 'Failed to get course answer.');
    } finally {
      setCourseAsking(false);
    }
  };

  const renderSources = (sources: QueryResponse['sources']) => {
    if (!sources || sources.length === 0) return null;
    return (
      <div className="mt-4">
        <p className="text-sm font-semibold text-gray-900 mb-2">Sources</p>
        <div className="space-y-1">
          {sources.map((source, index) => (
            <div key={`${source.lecture_id}-${index}`} className="text-sm text-gray-600">
              <span className="font-medium text-primary-600">
                {source.lecture_name || 'Lecture'}
              </span>
              {describeSource(source) && `, ${describeSource(source)}`}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
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
              {(user?.role === 'instructor' || user?.role === 'admin') ? (
                <Link
                  href="/instructor"
                  className="text-sm font-medium text-gray-700 hover:text-primary-600"
                >
                  Analytics
                </Link>
              ) : null}
              <Link
                href="/"
                className="text-sm font-medium text-gray-700 hover:text-primary-600"
              >
                Courses
              </Link>
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

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Manage Your Courses</h2>
          <p className="text-gray-600">
            Group lectures into courses, upload new material, and ask questions across multiple lectures.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="space-y-8">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Create Course</h3>
              <form className="space-y-4" onSubmit={handleCreateCourse}>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Course Name</label>
                  <input
                    type="text"
                    value={newCourseName}
                    onChange={(e) => setNewCourseName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="e.g. CS101 - Algorithms"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={newCourseDescription}
                    onChange={(e) => setNewCourseDescription(e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="Optional course description"
                  />
                </div>
                {courseFormError && (
                  <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">
                    {courseFormError}
                  </div>
                )}
                <button
                  type="submit"
                  disabled={creatingCourse}
                  className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {creatingCourse ? 'Creating...' : 'Create Course'}
                </button>
              </form>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Courses ({courses.length})
                </h3>
                {refreshing && (
                  <div className="flex items-center space-x-2 text-sm text-gray-500">
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Refreshing...</span>
                  </div>
                )}
              </div>
              {loadingCourses ? (
                <div className="text-center py-12">
                  <svg className="w-8 h-8 animate-spin mx-auto text-primary-500" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <p className="mt-4 text-gray-500">Loading courses...</p>
                </div>
              ) : courses.length === 0 ? (
                <p className="text-sm text-gray-500">Create your first course to get started.</p>
              ) : (
                <div className="space-y-2">
                  {courses.map(course => (
                    <button
                      key={course.id}
                      onClick={() => {
                        setSelectedCourseId(course.id);
                        setCourseAnswer(null);
                      }}
                      className={`w-full text-left p-4 rounded-lg border transition-all ${
                        selectedCourseId === course.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-primary-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-gray-900">{course.name}</p>
                          {course.description && (
                            <p className="text-sm text-gray-500 truncate">{course.description}</p>
                          )}
                        </div>
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700">
                          {course.lecture_count} lectures
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-8">
            {!selectedCourse ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-10 text-center">
                <p className="text-gray-500">Select or create a course to begin uploading lectures.</p>
              </div>
            ) : (
              <>
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div>
                      <h3 className="text-2xl font-bold text-gray-900">{selectedCourse.name}</h3>
                      {selectedCourse.description && (
                        <p className="text-gray-600 mt-1">{selectedCourse.description}</p>
                      )}
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-sm text-gray-500">
                        {selectedCourse.lecture_count} lectures
                      </span>
                      <span className="w-2 h-2 rounded-full bg-green-500" title="Course ready" />
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Upload Lecture</h3>
                  <FileUpload courseId={selectedCourse.id} onUploadSuccess={handleUploadSuccess} />
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Ask Across Lectures</h3>
                  <form onSubmit={handleCourseQuery} className="space-y-4">
                    <textarea
                      value={courseQuestion}
                      onChange={(e) => setCourseQuestion(e.target.value)}
                      placeholder={`Ask a question about ${selectedCourse.name}...`}
                      rows={3}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      disabled={courseAsking}
                    />
                    <div className="flex items-center space-x-4">
                      <button
                        type="submit"
                        disabled={!courseQuestion.trim() || courseAsking}
                        className="px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {courseAsking ? 'Searching...' : 'Ask Course'}
                      </button>
                      {courseAsking && (
                        <div className="flex items-center space-x-2 text-sm text-gray-500">
                          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <span>Gathering context...</span>
                        </div>
                      )}
                    </div>
                  </form>
                  {queryError && (
                    <div className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
                      {queryError}
                    </div>
                  )}
                  {courseAnswer && (
                    <div className="mt-6 border border-gray-200 rounded-lg p-4 bg-gray-50">
                      <p className="text-gray-800 whitespace-pre-wrap">{courseAnswer.answer}</p>
                      {courseAnswer.citation && (
                        <p className="mt-2 text-sm text-primary-600 font-medium">
                          {courseAnswer.citation}
                        </p>
                      )}
                      {renderSources(courseAnswer.sources)}
                    </div>
                  )}
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">
                      Lectures in {selectedCourse.name} ({selectedLectures.length})
                    </h3>
                  </div>
                  <LectureList lectures={selectedLectures} onDelete={handleDelete} />
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

