'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
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

// Course Analytics Component
function CourseAnalyticsOverview({ courseId }: { courseId: number }) {
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, [courseId]);

  const loadAnalytics = async () => {
    try {
      const data = await apiClient.getCourseAnalytics(courseId);
      setAnalytics(data);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="text-center py-8">
          <svg className="w-8 h-8 animate-spin mx-auto text-primary-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="mt-4 text-gray-500">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <p className="text-gray-500">No analytics data available yet.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6">Course Analytics Overview</h3>
      
      <div className="mb-6">
        <p className="text-sm text-gray-600 mb-4">How are students interacting with this course?</p>
        
        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-xs text-gray-500 mb-1">Total Questions</p>
            <p className="text-2xl font-bold text-gray-900">{analytics.total_questions}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-xs text-gray-500 mb-1">Active Students</p>
            <p className="text-2xl font-bold text-gray-900">{analytics.active_students}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-xs text-gray-500 mb-1">Top Confused Topic</p>
            <p className="text-sm font-semibold text-gray-900 line-clamp-2">
              {analytics.top_confused_topics?.[0]?.topic || 'N/A'}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-xs text-gray-500 mb-1">Trend (Last 7 days)</p>
            <div className="flex items-center">
              {analytics.trend_direction === 'up' ? (
                <span className="text-red-600 font-semibold">↑ +{analytics.trend_percentage}%</span>
              ) : analytics.trend_direction === 'down' ? (
                <span className="text-green-600 font-semibold">↓ -{analytics.trend_percentage}%</span>
              ) : (
                <span className="text-gray-600 font-semibold">→ Stable</span>
              )}
            </div>
          </div>
        </div>

        {/* Course Overview Summary */}
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4 mb-6">
          <h4 className="font-semibold text-gray-900 mb-2">Course Overview</h4>
          <ul className="text-sm text-gray-700 space-y-1">
            <li>• {analytics.total_questions} questions asked</li>
            <li>• {analytics.top_confused_topics?.length || 0} recurring topics</li>
            {analytics.trend_direction === 'up' && (
              <li className="text-red-600">• Confusion increased this week (+{analytics.trend_percentage}%)</li>
            )}
            {analytics.trend_direction === 'down' && (
              <li className="text-green-600">• Confusion decreased this week (-{analytics.trend_percentage}%)</li>
            )}
          </ul>
        </div>

        {/* Top Confused Topics */}
        {analytics.top_confused_topics && analytics.top_confused_topics.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-900 mb-3">Top Confused Topics</h4>
            <div className="space-y-2">
              {analytics.top_confused_topics.map((topic: any, index: number) => (
                <div key={index} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                  <div className="flex items-start justify-between mb-1">
                    <p className="font-medium text-gray-900">
                      {index + 1}. {topic.topic}
                    </p>
                    <span className="text-xs text-gray-500 bg-white px-2 py-1 rounded">
                      {topic.count} questions
                    </span>
                  </div>
                  {topic.questions && topic.questions.length > 0 && (
                    <div className="mt-2 text-xs text-gray-600 space-y-1">
                      {topic.questions.slice(0, 2).map((q: string, i: number) => (
                        <p key={i} className="pl-2 border-l-2 border-gray-300">"{q}"</p>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CourseDetailPage() {
  const router = useRouter();
  const params = useParams();
  const courseId = parseInt(params.id as string);
  
  const [user, setUser] = useState<User | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [courseQuestion, setCourseQuestion] = useState('');
  const [courseAsking, setCourseAsking] = useState(false);
  const [courseAnswer, setCourseAnswer] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [expandedCourseId, setExpandedCourseId] = useState<number | null>(null);
  const [courseStudents, setCourseStudents] = useState<Record<number, { student_id: number; student_email: string }[]>>({});
  const [addingStudent, setAddingStudent] = useState<Record<number, boolean>>({});
  const [newStudentEmail, setNewStudentEmail] = useState<Record<number, string>>({});
  const [studentError, setStudentError] = useState<Record<number, string | null>>({});
  const [loadingStudents, setLoadingStudents] = useState<Record<number, boolean>>({});

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

  const loadCourse = useCallback(async () => {
    try {
      const coursesResponse = await apiClient.getCourses();
      const foundCourse = coursesResponse.courses.find(c => c.id === courseId);
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
      loadCourse();
    }
  }, [user, courseId, loadCourse]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (course) {
        const hasProcessing = course.lectures.some(lecture => lecture.status === 'processing');
        if (hasProcessing) {
          loadCourse();
        }
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [course, loadCourse]);

  const handleUploadSuccess = () => {
    setRefreshing(true);
    loadCourse();
  };

  const handleDelete = async (id: number) => {
    try {
      await apiClient.deleteLecture(id);
      await loadCourse();
    } catch (error) {
      console.error('Failed to delete lecture:', error);
      alert('Failed to delete lecture');
    }
  };

  const handleCourseQuery = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!course || !courseQuestion.trim()) {
      return;
    }
    setCourseAsking(true);
    setQueryError(null);
    setCourseAnswer(null);
    try {
      const response = await apiClient.queryCourse(course.id, courseQuestion);
      setCourseAnswer(response);
      setCourseQuestion('');
    } catch (error: any) {
      console.error('Failed to query course:', error);
      setQueryError(error.response?.data?.detail || 'Failed to get course answer.');
    } finally {
      setCourseAsking(false);
    }
  };

  const loadCourseStudents = async (courseId: number) => {
    if (user?.role !== 'instructor') return;
    
    setLoadingStudents({ ...loadingStudents, [courseId]: true });
    setStudentError({ ...studentError, [courseId]: null });
    try {
      const students = await apiClient.getCourseStudents(courseId);
      setCourseStudents({ ...courseStudents, [courseId]: students });
    } catch (error: any) {
      setStudentError({ ...studentError, [courseId]: error.response?.data?.detail || 'Failed to load students' });
    } finally {
      setLoadingStudents({ ...loadingStudents, [courseId]: false });
    }
  };

  const handleAddStudent = async (courseId: number) => {
    const email = newStudentEmail[courseId]?.trim();
    if (!email) {
      setStudentError({ ...studentError, [courseId]: 'Email is required' });
      return;
    }

    setAddingStudent({ ...addingStudent, [courseId]: true });
    setStudentError({ ...studentError, [courseId]: null });
    try {
      await apiClient.addStudentToCourse(courseId, email);
      setNewStudentEmail({ ...newStudentEmail, [courseId]: '' });
      await loadCourseStudents(courseId);
    } catch (error: any) {
      setStudentError({ ...studentError, [courseId]: error.response?.data?.detail || 'Failed to add student' });
    } finally {
      setAddingStudent({ ...addingStudent, [courseId]: false });
    }
  };

  const handleRemoveStudent = async (courseId: number, studentId: number) => {
    if (!confirm('Are you sure you want to remove this student from the course?')) {
      return;
    }

    try {
      await apiClient.removeStudentFromCourse(courseId, studentId);
      await loadCourseStudents(courseId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to remove student');
    }
  };

  const renderStudentManagement = (courseId: number) => {
    const students = courseStudents[courseId] || [];
    const isLoading = loadingStudents[courseId];
    const isAdding = addingStudent[courseId];
    const error = studentError[courseId];
    const email = newStudentEmail[courseId] || '';

    return (
      <div className="space-y-3">
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Add Student</h4>
          <div className="flex gap-2">
            <input
              type="email"
              value={email}
              onChange={(e) => setNewStudentEmail({ ...newStudentEmail, [courseId]: e.target.value })}
              placeholder="student@example.com"
              className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddStudent(courseId);
                }
              }}
            />
            <button
              onClick={() => handleAddStudent(courseId)}
              disabled={isAdding}
              className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAdding ? 'Adding...' : 'Add'}
            </button>
          </div>
          {error && (
            <p className="mt-1 text-xs text-red-600">{error}</p>
          )}
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">
            Enrolled Students ({students.length})
          </h4>
          {isLoading ? (
            <p className="text-xs text-gray-500">Loading...</p>
          ) : students.length === 0 ? (
            <p className="text-xs text-gray-500">No students enrolled yet</p>
          ) : (
            <div className="space-y-1">
              {students.map((student) => (
                <div
                  key={student.student_id}
                  className="flex items-center justify-between px-3 py-2 bg-white border border-gray-200 rounded text-sm"
                >
                  <span className="text-gray-700">{student.student_email}</span>
                  <button
                    onClick={() => handleRemoveStudent(courseId, student.student_id)}
                    className="text-red-600 hover:text-red-700 text-xs font-medium"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <svg className="w-8 h-8 animate-spin mx-auto text-primary-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="mt-4 text-gray-500">Loading course...</p>
        </div>
      </div>
    );
  }

  if (!course) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/" className="text-xl font-bold text-primary-600 hover:text-primary-700">
                ← Back
              </Link>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">{course.name}</h1>
                {course.description && (
                  <p className="text-sm text-gray-500">{course.description}</p>
                )}
                <p className="text-xs text-gray-400 mt-1">{course.lecture_count} lectures</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {user?.role === 'instructor' && (
                <Link
                  href="/instructor"
                  className="text-sm text-gray-700 hover:text-gray-900"
                >
                  Analytics
                </Link>
              )}
              <button
                onClick={() => {
                  apiClient.logout();
                  router.push('/auth/login');
                }}
                className="text-sm text-gray-700 hover:text-gray-900"
              >
                Logout
              </button>
              <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                {user?.email?.charAt(0).toUpperCase() || 'U'}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Sidebar - Lectures */}
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Lectures</h3>
                {refreshing && (
                  <div className="flex items-center space-x-2 text-sm text-gray-500">
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                )}
              </div>
              {user?.role === 'instructor' && (
                <FileUpload
                  courseId={course.id}
                  onUploadSuccess={handleUploadSuccess}
                />
              )}
              <div className="mt-4">
                <LectureList
                  lectures={course.lectures}
                  onDelete={user?.role === 'instructor' ? handleDelete : () => {}}
                />
              </div>
            </div>

            {user?.role === 'instructor' && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <button
                  onClick={async () => {
                    if (expandedCourseId === course.id) {
                      setExpandedCourseId(null);
                    } else {
                      setExpandedCourseId(course.id);
                      await loadCourseStudents(course.id);
                    }
                  }}
                  className="w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center justify-between"
                >
                  <span>Manage Students</span>
                  <svg
                    className={`w-4 h-4 transition-transform ${expandedCourseId === course.id ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {expandedCourseId === course.id && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    {renderStudentManagement(course.id)}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Main Content - Chat or Analytics */}
          <div className="lg:col-span-2 space-y-8">
            {user?.role === 'instructor' ? (
              <CourseAnalyticsOverview courseId={course.id} />
            ) : (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Ask Questions</h3>
                <form onSubmit={handleCourseQuery} className="space-y-4">
                  <div>
                    <textarea
                      value={courseQuestion}
                      onChange={(e) => setCourseQuestion(e.target.value)}
                      placeholder="Ask a question about the course content..."
                      rows={4}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                      disabled={courseAsking || course.lecture_count === 0}
                    />
                    {course.lecture_count === 0 && (
                      <p className="mt-2 text-sm text-gray-500">
                        Upload at least one lecture to ask questions.
                      </p>
                    )}
                  </div>
                  {queryError && (
                    <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">
                      {queryError}
                    </div>
                  )}
                  <button
                    type="submit"
                    disabled={courseAsking || !courseQuestion.trim() || course.lecture_count === 0}
                    className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {courseAsking ? 'Asking...' : 'Ask Question'}
                  </button>
                </form>

                {courseAnswer && (
                  <div className="mt-6 pt-6 border-t border-gray-200">
                    <div className="prose max-w-none">
                      <p className="text-gray-800 whitespace-pre-wrap">{courseAnswer.answer}</p>
                      {renderSources(courseAnswer.sources)}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

