'use client';

/**
 * This hook manages state and actions for the course detail page workflow.
 * It loads data, tracks UI state, and returns handlers used by page components.
 */
import { useEffect, useRef, useState } from 'react';
import {
  apiClient,
  CourseStudent,
  LectureHealthMetric,
  QueryResponse,
  UploadRequest,
} from '@/lib/api';
import { describeSource } from '@/lib/formatters';
import { useCoursePage } from '@/hooks/useCoursePage';

type RouterLike = {
  push: (href: string) => void;
};

export type CourseDetailCategory =
  | 'all'
  | 'analytics'
  | 'lectures'
  | 'students'
  | 'uploads'
  | 'announcements'
  | 'questions';

export function useCourseDetailPage(courseId: number, router: RouterLike) {
  const instructorCategories: CourseDetailCategory[] = ['all', 'analytics', 'lectures', 'students', 'uploads', 'announcements'];
  const studentCategories: CourseDetailCategory[] = ['all', 'lectures', 'uploads', 'announcements', 'questions'];

  const { user, course, loading, refreshing, setRefreshing, loadCourse } = useCoursePage(courseId, router);
  const [activeCategory, setActiveCategory] = useState<CourseDetailCategory>('all');
  const [courseQuestion, setCourseQuestion] = useState('');
  const [courseAsking, setCourseAsking] = useState(false);
  const [courseAnswer, setCourseAnswer] = useState<QueryResponse | null>(null);
  const [courseChatMessages, setCourseChatMessages] = useState<{ question: string; answer: QueryResponse | null }[]>([]);
  const [queryError, setQueryError] = useState<string | null>(null);
  const courseChatEndRef = useRef<HTMLDivElement>(null);
  const [courseStudents, setCourseStudents] = useState<Record<number, CourseStudent[]>>({});
  const [addingStudent, setAddingStudent] = useState<Record<number, boolean>>({});
  const [newStudentEmail, setNewStudentEmail] = useState<Record<number, string>>({});
  const [studentError, setStudentError] = useState<Record<number, string | null>>({});
  const [loadingStudents, setLoadingStudents] = useState<Record<number, boolean>>({});
  const [studentRole, setStudentRole] = useState<Record<number, 'student' | 'ta'>>({});
  const [showManageStudents, setShowManageStudents] = useState<Record<number, boolean>>({});
  const [showStudentsMore, setShowStudentsMore] = useState<Record<number, boolean>>({});
  const [announcements, setAnnouncements] = useState<Record<number, { id: number; message: string; created_at?: string | null }[]>>({});
  const [newAnnouncement, setNewAnnouncement] = useState<Record<number, string>>({});
  const [announcementError, setAnnouncementError] = useState<Record<number, string | null>>({});
  const [postingAnnouncement, setPostingAnnouncement] = useState<Record<number, boolean>>({});
  const [uploadRequests, setUploadRequests] = useState<Record<number, UploadRequest[]>>({});
  const [loadingUploadRequests, setLoadingUploadRequests] = useState<Record<number, boolean>>({});
  const [canReviewUploads, setCanReviewUploads] = useState<Record<number, boolean>>({});
  const [myUploadRequests, setMyUploadRequests] = useState<Record<number, UploadRequest[]>>({});
  const [loadingMyUploadRequests, setLoadingMyUploadRequests] = useState<Record<number, boolean>>({});
  const [showAllInstructorLectures, setShowAllInstructorLectures] = useState<Record<number, boolean>>({});
  const [showAllStudentLectures, setShowAllStudentLectures] = useState<Record<number, boolean>>({});
  const [collapseLectures, setCollapseLectures] = useState<Record<number, boolean>>({});
  const [collapseUploadRequests, setCollapseUploadRequests] = useState<Record<number, boolean>>({});
  const [collapseStudentAnnouncements, setCollapseStudentAnnouncements] = useState<Record<number, boolean>>({});
  const [collapseAskQuestions, setCollapseAskQuestions] = useState<Record<number, boolean>>({});
  const [collapseInstructorAnnouncements, setCollapseInstructorAnnouncements] = useState<Record<number, boolean>>({});
  const [collapseManageStudents, setCollapseManageStudents] = useState<Record<number, boolean>>({});
  const [lectureHealthByCourse, setLectureHealthByCourse] = useState<Record<number, LectureHealthMetric[]>>({});

  useEffect(() => {
    setCourseChatMessages([]);
    setQueryError(null);
    setCourseAnswer(null);
  }, [courseId]);

  useEffect(() => {
    if (user && courseId) {
      loadAnnouncements(courseId);
    }
  }, [user, courseId]);

  useEffect(() => {
    if (user?.role === 'student' && courseId) {
      loadMyUploadRequests(courseId);
    }
  }, [user?.role, courseId]);

  useEffect(() => {
    if (user?.role === 'instructor' && courseId) {
      apiClient
        .getLectureHealth(courseId)
        .then((response) => {
          setLectureHealthByCourse((prev) => ({ ...prev, [courseId]: response.lectures }));
        })
        .catch((error) => {
          console.error('Failed to load lecture health:', error);
        });
    }
  }, [user?.role, courseId]);

  useEffect(() => {
    if ((user?.role === 'instructor' || user?.role === 'ta') && courseId) {
      loadUploadRequests(courseId);
    }
  }, [user?.role, courseId]);

  useEffect(() => {
    if (!user?.role) return;
    const allowed = user.role === 'instructor' ? instructorCategories : studentCategories;
    if (!allowed.includes(activeCategory)) {
      setActiveCategory('all');
    }
  }, [user?.role, activeCategory, instructorCategories, studentCategories]);

  useEffect(() => {
    if (user?.role === 'instructor' && courseId) {
      loadCourseStudents(courseId);
    }
  }, [user?.role, courseId]);

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

  const handleDelete = async (id: number) => {
    try {
      await apiClient.deleteLecture(id);
      await loadCourse();
    } catch (error) {
      console.error('Failed to delete lecture:', error);
      alert('Failed to delete lecture');
    }
  };

  const handleUploadSuccess = () => {
    setRefreshing(true);
    void loadCourse();
  };

  const handleLeaveCourse = async () => {
    if (!course) return;
    if (!confirm('Leave this course? You will lose access to its lectures.')) {
      return;
    }
    try {
      await apiClient.leaveCourse(course.id);
      router.push('/');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to leave course');
    }
  };

  const handleCourseQuery = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!course || !courseQuestion.trim()) {
      return;
    }
    const questionText = courseQuestion.trim();
    setCourseQuestion('');
    setCourseAsking(true);
    setQueryError(null);
    setCourseAnswer(null);
    setCourseChatMessages((prev) => [...prev, { question: questionText, answer: null }]);
    try {
      const response = await apiClient.queryCourse(course.id, questionText);
      setCourseChatMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { question: next[next.length - 1].question, answer: response };
        return next;
      });
    } catch (error: any) {
      console.error('Failed to query course:', error);
      setQueryError(error.response?.data?.detail || 'Failed to get course answer.');
      setCourseChatMessages((prev) => prev.slice(0, -1));
    } finally {
      setCourseAsking(false);
    }
  };

  useEffect(() => {
    courseChatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [courseChatMessages, courseAsking]);

  const loadCourseStudents = async (courseId: number) => {
    if (user?.role !== 'instructor') return;

    setLoadingStudents((prev) => ({ ...prev, [courseId]: true }));
    setStudentError((prev) => ({ ...prev, [courseId]: null }));
    try {
      const students = await apiClient.getCourseStudents(courseId);
      setCourseStudents((prev) => ({ ...prev, [courseId]: students }));
    } catch (error: any) {
      setStudentError((prev) => ({
        ...prev,
        [courseId]: error.response?.data?.detail || 'Failed to load students',
      }));
    } finally {
      setLoadingStudents((prev) => ({ ...prev, [courseId]: false }));
    }
  };

  const loadAnnouncements = async (courseId: number) => {
    try {
      const response = await apiClient.getAnnouncements(courseId);
      setAnnouncements((prev) => ({ ...prev, [courseId]: response.announcements }));
    } catch (error) {
      console.error('Failed to load announcements:', error);
    }
  };

  const loadUploadRequests = async (courseId: number) => {
    setLoadingUploadRequests((prev) => ({ ...prev, [courseId]: true }));
    try {
      const response = await apiClient.getUploadRequests(courseId, 'pending');
      setUploadRequests((prev) => ({ ...prev, [courseId]: response.requests }));
      setCanReviewUploads((prev) => ({ ...prev, [courseId]: true }));
    } catch (error: any) {
      if (error.response?.status === 403) {
        setCanReviewUploads((prev) => ({ ...prev, [courseId]: false }));
      } else {
        console.error('Failed to load upload requests:', error);
      }
    } finally {
      setLoadingUploadRequests((prev) => ({ ...prev, [courseId]: false }));
    }
  };

  const loadMyUploadRequests = async (courseId: number) => {
    setLoadingMyUploadRequests((prev) => ({ ...prev, [courseId]: true }));
    try {
      const response = await apiClient.getMyUploadRequests(courseId);
      setMyUploadRequests((prev) => ({ ...prev, [courseId]: response.requests }));
    } catch (error) {
      console.error('Failed to load my upload requests:', error);
    } finally {
      setLoadingMyUploadRequests((prev) => ({ ...prev, [courseId]: false }));
    }
  };

  const refreshUploadRequestState = async (courseId: number, options?: { reloadCourse?: boolean }) => {
    const tasks: Promise<unknown>[] = [loadMyUploadRequests(courseId)];
    if (user?.role === 'instructor' || user?.role === 'ta') {
      tasks.push(loadUploadRequests(courseId));
    }
    if (options?.reloadCourse) {
      tasks.push(loadCourse());
    }
    await Promise.all(tasks);
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
      const role = studentRole[courseId] || 'student';
      await apiClient.addStudentToCourse(courseId, email, role);
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

  const handleUpdateStudent = async (
    courseId: number,
    studentId: number,
    payload: { role?: 'student' | 'ta' }
  ) => {
    try {
      await apiClient.updateStudentAssignment(courseId, studentId, payload);
      await loadCourseStudents(courseId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update student');
    }
  };

  const handlePostAnnouncement = async (courseId: number) => {
    const message = newAnnouncement[courseId]?.trim();
    if (!message) return;
    setPostingAnnouncement({ ...postingAnnouncement, [courseId]: true });
    setAnnouncementError({ ...announcementError, [courseId]: null });
    try {
      await apiClient.createAnnouncement(courseId, message);
      setNewAnnouncement({ ...newAnnouncement, [courseId]: '' });
      await loadAnnouncements(courseId);
    } catch (error: any) {
      setAnnouncementError({ ...announcementError, [courseId]: error.response?.data?.detail || 'Failed to post announcement' });
    } finally {
      setPostingAnnouncement({ ...postingAnnouncement, [courseId]: false });
    }
  };

  const handleApproveUpload = async (courseId: number, requestId: number) => {
    try {
      await apiClient.approveUploadRequest(courseId, requestId);
      await refreshUploadRequestState(courseId, { reloadCourse: true });
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to approve upload');
    }
  };

  const handleRejectUpload = async (courseId: number, requestId: number) => {
    try {
      await apiClient.rejectUploadRequest(courseId, requestId);
      await refreshUploadRequestState(courseId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to reject upload');
    }
  };

  const handleDeleteUploadRequest = async (courseId: number, requestId: number, status: string) => {
    const actionLabel = status === 'pending' ? 'cancel this upload request' : 'remove this upload request';
    if (!confirm(`Are you sure you want to ${actionLabel}?`)) {
      return;
    }

    try {
      await apiClient.deleteUploadRequest(courseId, requestId);
      await refreshUploadRequestState(courseId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to remove upload request');
    }
  };

  const renderStudentManagement = (courseId: number) => {
    const students = courseStudents[courseId] || [];
    const isLoading = loadingStudents[courseId];
    const isAdding = addingStudent[courseId];
    const error = studentError[courseId];
    const email = newStudentEmail[courseId] || '';
    const role = studentRole[courseId] || 'student';

    return (
      <div className="space-y-4">
        <div>
          <h4 className="text-base font-medium text-gray-900 mb-2">Add Student</h4>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              type="email"
              value={email}
              onChange={(e) => setNewStudentEmail({ ...newStudentEmail, [courseId]: e.target.value })}
              placeholder="student@example.com"
              className="flex-1 px-4 py-2 text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddStudent(courseId);
                }
              }}
            />
            <select
              value={role}
              onChange={(e) => setStudentRole({ ...studentRole, [courseId]: e.target.value as 'student' | 'ta' })}
              className="px-4 py-2 text-base border border-gray-300 rounded-lg min-w-[100px]"
            >
              <option value="student">Student</option>
              <option value="ta">TA</option>
            </select>
            <button
              onClick={() => handleAddStudent(courseId)}
              disabled={isAdding}
              className="px-4 py-2 text-base bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAdding ? 'Adding...' : 'Add'}
            </button>
          </div>
          {error && (
            <p className="mt-1 text-sm text-red-600">{error}</p>
          )}
        </div>

        <div>
          <h4 className="text-base font-medium text-gray-900 mb-2">
            Enrolled Students ({students.length})
          </h4>
          <div className="flex flex-wrap gap-2 mb-3">
            <button
              onClick={() => setShowManageStudents({ ...showManageStudents, [courseId]: true })}
              className="px-4 py-2 text-base rounded-full border border-gray-200 text-gray-700"
            >
              Manage Students
            </button>
            <button
              onClick={() => setShowStudentsMore({ ...showStudentsMore, [courseId]: true })}
              className="px-4 py-2 text-base rounded-full border border-dashed border-gray-300 text-gray-600"
            >
              Show More
            </button>
          </div>
          {isLoading ? (
            <p className="text-sm text-gray-500">Loading...</p>
          ) : students.length === 0 ? (
            <p className="text-sm text-gray-500">No students enrolled yet</p>
          ) : (
            <div className="space-y-2">
              {students.map((student, index) => (
                <div
                  key={student.student_id}
                  className="w-full flex items-center justify-between px-3 py-2 bg-white border border-gray-200 rounded text-base"
                >
                  <span className="text-gray-500 text-sm w-6">{index + 1}.</span>
                  <span className="flex-1 text-gray-800">{student.student_email}</span>
                  <span className="text-gray-500 text-sm">{student.role}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {showManageStudents[courseId] && (
          <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-6">
            <div className="bg-white rounded-xl shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto p-8">
              <div className="flex items-center justify-between mb-6">
                <h4 className="text-xl font-semibold text-gray-900">Manage Students</h4>
                <button
                  onClick={() => setShowManageStudents({ ...showManageStudents, [courseId]: false })}
                  className="text-gray-400 hover:text-gray-600 text-2xl p-2"
                >
                  ✕
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">#</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Email</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Role</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Activity</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {students.map((student, index) => (
                      <tr key={student.student_id}>
                        <td className="px-4 py-3 text-base text-gray-500">{index + 1}</td>
                        <td className="px-4 py-3 text-base text-gray-900">{student.student_email}</td>
                        <td className="px-4 py-3">
                          <select
                            value={student.role}
                            onChange={async (e) => {
                              await handleUpdateStudent(courseId, student.student_id, { role: e.target.value as 'student' | 'ta' });
                              await loadCourseStudents(courseId);
                            }}
                            className="px-3 py-2 text-base border border-gray-300 rounded-lg min-w-[100px]"
                          >
                            <option value="student">Student</option>
                            <option value="ta">TA</option>
                          </select>
                        </td>
                        <td className="px-4 py-3 text-base text-gray-600">
                          {student.questions_count} q{student.questions_count === 1 ? '' : 's'}
                          {student.last_active && (
                            <span className="block text-sm text-gray-400">
                              {new Date(student.last_active).toLocaleDateString()}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => handleRemoveStudent(courseId, student.student_id)}
                            className="text-red-600 hover:text-red-700 text-base font-medium"
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {showStudentsMore[courseId] && (
          <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-6">
            <div className="bg-white rounded-xl shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto p-8">
              <div className="flex items-center justify-between mb-6">
                <h4 className="text-xl font-semibold text-gray-900">Student Details</h4>
                <button
                  onClick={() => setShowStudentsMore({ ...showStudentsMore, [courseId]: false })}
                  className="text-gray-400 hover:text-gray-600 text-2xl p-2"
                >
                  ✕
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">#</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Email</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Role</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Activity</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {students.map((student, index) => (
                      <tr key={student.student_id}>
                        <td className="px-4 py-3 text-base text-gray-500">{index + 1}</td>
                        <td className="px-4 py-3 text-base text-gray-900">{student.student_email}</td>
                        <td className="px-4 py-3 text-base text-gray-700">{student.role}</td>
                        <td className="px-4 py-3 text-base text-gray-600">
                          {student.questions_count} q{student.questions_count === 1 ? '' : 's'}
                          {student.last_active && (
                            <span className="block text-sm text-gray-400">
                              {new Date(student.last_active).toLocaleDateString()}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderSources = (sources: QueryResponse['sources']) => {
    if (!sources || sources.length === 0) return null;
    return (
      <div className="mt-4">
        <p className="text-base font-semibold text-gray-900 mb-2">Sources</p>
        <div className="space-y-1">
          {sources.map((source, index) => (
            <div key={`${source.lecture_id}-${index}`} className="text-base text-gray-600">
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

  const instructorLectures = course?.lectures.filter((lecture) => lecture.created_by_role === 'instructor') ?? [];
  const studentLectures = course?.lectures.filter((lecture) => lecture.created_by_role !== 'instructor') ?? [];
  const lectureHealth = course ? lectureHealthByCourse[course.id] || [] : [];
  const lectureQuestionsById = lectureHealth.reduce<Record<number, number>>((acc, item) => {
    acc[item.lecture_id] = item.query_count;
    return acc;
  }, {});
  const avgQuestions =
    lectureHealth.length > 0
      ? lectureHealth.reduce((sum, item) => sum + item.query_count, 0) / lectureHealth.length
      : 0;
  const showAllInstructor = course ? showAllInstructorLectures[course.id] ?? false : false;
  const showAllStudents = course ? showAllStudentLectures[course.id] ?? false : false;
  const visibleInstructorLectures = showAllInstructor ? instructorLectures : instructorLectures.slice(0, 4);
  const visibleStudentLectures = showAllStudents ? studentLectures : studentLectures.slice(0, 4);
  const categoryOptions = user?.role === 'instructor' ? instructorCategories : studentCategories;
  const showLectures = activeCategory === 'all' || activeCategory === 'lectures';
  const showManageStudentsSection = activeCategory === 'all' || activeCategory === 'students';
  const showUploads = activeCategory === 'all' || activeCategory === 'uploads';
  const showAnnouncements = activeCategory === 'all' || activeCategory === 'announcements';
  const showQuestions = activeCategory === 'all' || activeCategory === 'questions';
  const showAnalytics = activeCategory === 'all' || activeCategory === 'analytics';

  const handleLogout = () => {
    apiClient.logout();
    router.push('/auth/login');
  };

  return {
    activeCategory,
    addingStudent,
    announcementError,
    announcements,
    avgQuestions,
    canReviewUploads,
    categoryOptions,
    collapseAskQuestions,
    collapseInstructorAnnouncements,
    collapseLectures,
    collapseManageStudents,
    collapseStudentAnnouncements,
    collapseUploadRequests,
    course,
    courseAnswer,
    courseAsking,
    courseChatEndRef,
    courseChatMessages,
    courseQuestion,
    handleApproveUpload,
    handleCourseQuery,
    handleDelete,
    handleDeleteUploadRequest,
    handleLeaveCourse,
    handleLogout,
    handlePostAnnouncement,
    handleRejectUpload,
    handleUploadSuccess,
    instructorLectures,
    lectureQuestionsById,
    loadAnnouncements,
    loadCourseStudents,
    loading,
    loadingMyUploadRequests,
    loadingStudents,
    loadingUploadRequests,
    loadMyUploadRequests,
    loadUploadRequests,
    myUploadRequests,
    newAnnouncement,
    newStudentEmail,
    postingAnnouncement,
    queryError,
    refreshing,
    renderSources,
    renderStudentManagement,
    setActiveCategory,
    setCollapseAskQuestions,
    setCollapseInstructorAnnouncements,
    setCollapseLectures,
    setCollapseManageStudents,
    setCollapseStudentAnnouncements,
    setCollapseUploadRequests,
    setCourseQuestion,
    setNewAnnouncement,
    setShowAllInstructorLectures,
    setShowAllStudentLectures,
    showAllInstructor,
    showAllInstructorLectures,
    showAllStudents,
    showAllStudentLectures,
    showAnalytics,
    showAnnouncements,
    showLectures,
    showManageStudentsSection,
    showQuestions,
    showUploads,
    studentLectures,
    studentRole,
    uploadRequests,
    user,
    visibleInstructorLectures,
    visibleStudentLectures,
  };
}
