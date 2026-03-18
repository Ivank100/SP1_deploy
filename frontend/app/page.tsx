'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient, Course, User } from '@/lib/api';
import Link from 'next/link';
import CourseCard from '@/components/courses/CourseCard';
import { formatDate } from '@/lib/formatters';
import { filterVisibleCourses, groupCoursesBySemester, sortSemesterKeys } from '@/lib/courseGrouping';

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
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
  }, [hiddenTermKeys, hiddenPrefsLoaded]);

  // Refetch courses when tab becomes visible (e.g. student was added by instructor in another tab)
  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible' && user) {
        loadCourses();
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
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
        term_year: newCourseTermYear,
        term_number: newCourseTermNumber,
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

  const toggleHidden = (courseId: number) => {
    setHiddenCourseIds((prev) =>
      prev.includes(courseId) ? prev.filter((id) => id !== courseId) : [...prev, courseId]
    );
  };

  const toggleHiddenTerm = (termKey: string) => {
    setHiddenTermKeys((prev) =>
      prev.includes(termKey) ? prev.filter((key) => key !== termKey) : [...prev, termKey]
    );
  };

  const visibleCourses = filterVisibleCourses(courses, hiddenCourseIds, hiddenTermKeys, courseTab);

  const semesterGroups = groupCoursesBySemester(visibleCourses);

  const sortedSemesterKeys = sortSemesterKeys(semesterGroups);

  const toggleTerm = (termKey: string) => {
    setExpandedTerms((prev) => ({ ...prev, [termKey]: !prev[termKey] }));
  };

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

        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCourseTab('classes')}
              className={`px-5 py-2.5 rounded-full text-base font-medium border ${
                courseTab === 'classes' ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-700 border-gray-200'
              }`}
            >
              Classes
            </button>
            <button
              onClick={() => setCourseTab('hidden')}
              className={`px-5 py-2.5 rounded-full text-base font-medium border ${
                courseTab === 'hidden' ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-700 border-gray-200'
              }`}
            >
              Hidden
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode('semester')}
              className={`px-4 py-2 text-base rounded-full border ${
                viewMode === 'semester' ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-700 border-gray-200'
              }`}
            >
              Default
            </button>
            <button
              onClick={() => setViewMode('mindmap')}
              className={`px-4 py-2 text-base rounded-full border ${
                viewMode === 'mindmap' ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-700 border-gray-200'
              }`}
            >
              Mindmap
            </button>
          </div>
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
          <>
            {viewMode === 'mindmap' ? (
              <div className="relative min-h-[400px] py-4">
                <div className="flex items-center justify-between mb-8">
                  <div />
                  {user?.role === 'instructor' && (
                    <button
                      onClick={() => setShowCreateModal(true)}
                      className="px-5 py-2.5 text-base font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    >
                      Create Course
                    </button>
                  )}
                </div>
                <div className="relative pl-2">
                  <div
                    className="absolute left-0 top-0 bottom-0 w-0.5 bg-gray-300"
                    aria-hidden
                  />
                {sortedSemesterKeys.map((term, termIdx) => {
                  const courses = semesterGroups[term] ?? [];
                  const mid = Math.ceil(courses.length / 2);
                  const leftCourses = courses.slice(0, mid);
                  const rightCourses = courses.slice(mid);
                  const isExpanded = expandedTerms[term];
                  const [year] = term.split('/');

                  const CourseNode = ({ course }: { course: typeof courses[0] }) => (
                    <Link
                      href={`/courses/${course.id}`}
                      title={`Click to open · ${course.lecture_count} lectures`}
                      className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-4 py-3 text-base text-gray-700 shadow-sm hover:border-primary-400 hover:shadow-md transition-all"
                    >
                      <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary-100 text-primary-700 text-sm">
                        📘
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-base font-medium text-gray-900 truncate">{course.name}</p>
                        <p className="text-sm text-gray-500">{course.lecture_count} lectures</p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          toggleHidden(course.id);
                        }}
                        className="shrink-0 text-xs px-2 py-1 rounded-full border border-gray-200 text-gray-500 hover:text-gray-700"
                      >
                        {hiddenCourseIds.includes(course.id) ? 'Unhide' : 'Hide'}
                      </button>
                    </Link>
                  );

                  const strokeColor = '#6b7280';
                  const ConnectorSvg = ({ side, count }: { side: 'left' | 'right'; count: number }) => {
                    const w = 28;
                    const branchLen = 10;
                    const cy = 50;
                    if (count === 0) return null;
                    const paths: string[] = [];
                    if (count === 1) {
                      paths.push(`M ${side === 'left' ? w : 0},${cy} H ${side === 'left' ? 0 : w}`);
                    } else {
                      const stemX = side === 'left' ? branchLen : w - branchLen;
                      paths.push(`M ${side === 'left' ? w : 0},${cy} H ${stemX}`);
                      const yVals = Array.from({ length: count }, (_, i) => ((i + 0.5) / count) * 100);
                      paths.push(`M ${stemX},${Math.min(...yVals)} V ${Math.max(...yVals)}`);
                      yVals.forEach((y) => paths.push(`M ${stemX},${y} H ${side === 'left' ? 0 : w}`));
                    }
                    return (
                      <svg
                        className="shrink-0 self-center"
                        width={w}
                        height={100}
                        viewBox={`0 0 ${w} 100`}
                        preserveAspectRatio="none"
                        style={{ height: count > 0 ? Math.max(80, count * 64) : 80 }}
                      >
                        {paths.map((d, i) => (
                          <path
                            key={i}
                            d={d}
                            fill="none"
                            stroke={strokeColor}
                            strokeWidth="1.5"
                            vectorEffect="non-scaling-stroke"
                          />
                        ))}
                      </svg>
                    );
                  };

                  return (
                    <div
                      key={term}
                      className={`relative flex items-center gap-2 ${termIdx < sortedSemesterKeys.length - 1 ? 'mb-20' : ''}`}
                    >
                      <div className="flex-1 flex items-center justify-center gap-2 min-h-[11rem]">
                        <div className="flex flex-col justify-center gap-3 items-end min-w-[200px]">
                          {isExpanded && leftCourses.map((course) => (
                            <div key={course.id} className="flex items-center w-full justify-end">
                              <CourseNode course={course} />
                            </div>
                          ))}
                        </div>
                        {isExpanded && <ConnectorSvg side="left" count={leftCourses.length} />}
                      </div>
                      <div className="relative shrink-0">
                        <button
                          type="button"
                          onClick={() => toggleTerm(term)}
                          title={`Semester ${term} — ${courses.length} courses`}
                          className="w-44 h-44 rounded-full bg-primary-600 text-white flex flex-col items-center justify-center text-center shadow-lg border-4 border-white hover:bg-primary-700 transition-colors"
                        >
                          <span className="text-xs text-white/70 uppercase tracking-wide">{year}</span>
                          <span className="text-xl font-semibold">{term}</span>
                          <span className="text-sm text-white/80">{courses.length} courses</span>
                        </button>
                      </div>
                      <div className="flex-1 flex items-center justify-center gap-2 min-h-[11rem]">
                        {isExpanded && <ConnectorSvg side="right" count={rightCourses.length} />}
                        <div className="flex flex-col justify-center gap-3 items-start min-w-[200px]">
                          {isExpanded && rightCourses.map((course) => (
                            <div key={course.id} className="flex items-center w-full justify-start">
                              <CourseNode course={course} />
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
                </div>
                {sortedSemesterKeys.length === 0 && (
                  <p className="text-sm text-gray-500">No courses to show.</p>
                )}
              </div>
            ) : (
              <div>
                <div className="flex items-center justify-between mb-8">
                  <div />
                  {user?.role === 'instructor' && (
                    <button
                      onClick={() => setShowCreateModal(true)}
                      className="px-5 py-2.5 text-base font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    >
                      Create Course
                    </button>
                  )}
                  {user?.role === 'student' && (
                    <button
                      onClick={() => setShowJoinModal(true)}
                      className="px-5 py-2.5 text-base font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    >
                      Join with code
                    </button>
                  )}
                </div>
                <div className="space-y-8">
                {sortedSemesterKeys.map((groupKey) => (
                  <div key={groupKey}>
                    <h3 className="text-xl font-semibold text-gray-900 mb-4">{groupKey}</h3>
                    <div className="flex flex-wrap gap-4">
                      {semesterGroups[groupKey].map((course) => (
                        <CourseCard
                          key={course.id}
                          course={course}
                          createdDate={formatDate(course.created_at)}
                          isHidden={hiddenCourseIds.includes(course.id)}
                          onToggleHidden={toggleHidden}
                          userRole={user?.role}
                        />
                      ))}
                    </div>
                  </div>
                ))}
                {visibleCourses.length === 0 && (
                  <p className="text-sm text-gray-500">No courses to show.</p>
                )}
                </div>
              </div>
            )}
          </>
        )}

        {!loadingCourses && visibleCourses.length === 0 && user?.role !== 'instructor' && courseTab === 'classes' && (
          <div className="text-center py-20">
            <p className="text-gray-500">No courses available. Use a join code to get started.</p>
          </div>
        )}

        {!loadingCourses && visibleCourses.length === 0 && user?.role === 'instructor' && courseTab === 'classes' && (
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
                  setNewCourseTermYear(new Date().getFullYear());
                  setNewCourseTermNumber(1);
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
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Year</label>
                    <input
                      type="number"
                      min={2000}
                      max={2100}
                      value={newCourseTermYear}
                      onChange={(e) => setNewCourseTermYear(Number(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      placeholder="2025"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Term</label>
                    <select
                      value={newCourseTermNumber}
                      onChange={(e) => setNewCourseTermNumber(Number(e.target.value) as 1 | 2)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    >
                      <option value={1}>1</option>
                      <option value={2}>2</option>
                    </select>
                  </div>
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
                    setNewCourseTermYear(new Date().getFullYear());
                    setNewCourseTermNumber(1);
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
      {showJoinModal && user?.role === 'student' && (
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
