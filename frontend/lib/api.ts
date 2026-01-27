// API client for FastAPI backend
import axios from 'axios';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token');
    if (token) {
      if (!config.headers) {
        config.headers = {};
      }
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      console.warn('No auth token found in localStorage');
    }
  }
  return config;
});

// Handle 401 errors (unauthorized)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      window.location.href = '/auth/login';
    }
    return Promise.reject(error);
  }
);

export type FileType = 'pdf' | 'audio' | 'slides';

export interface Lecture {
  id: number;
  original_name: string;
  file_path: string;
  page_count: number;
  status: 'processing' | 'completed' | 'failed' | 'transcribing';
  created_at: string;
  course_id?: number | null;
  file_type: FileType;
  has_transcript: boolean;
}

export interface LectureListResponse {
  lectures: Lecture[];
  total: number;
}

export interface UploadResponse {
  lecture_id: number;
  message: string;
  status: string;
}

export interface CitationSource {
  lecture_id: number | null;
  lecture_name: string | null;
  page_number?: number | null;
  timestamp_start?: number | null;
  timestamp_end?: number | null;
   file_type?: FileType | null;
}

export interface QueryRequest {
  question: string;
  top_k?: number;
}

export interface QueryResponse {
  answer: string;
  citation: string;
  lecture_id: number | null;
  course_id: number | null;
  sources: CitationSource[];
}

export interface QueryHistoryItem {
  id: number;
  question: string;
  answer: string;
  created_at: string;
}

export interface QueryHistoryResponse {
  queries: QueryHistoryItem[];
  total: number;
}

export interface SummaryResponse {
  lecture_id: number;
  summary: string;
  cached: boolean;
}

export interface KeyPointsResponse {
  lecture_id: number;
  key_points: string[];
  cached: boolean;
}

export interface Flashcard {
  id: number;
  front?: string;
  back?: string;
  question?: string;
  answer?: string;
  page_number?: number | null;
  source_keypoint_id?: number | null;
  quality_score?: number | null;
}

export interface FlashcardListResponse {
  lecture_id: number;
  flashcards: Flashcard[];
  set_id?: number | null;
  strategy?: string | null;
}

export interface StudyMaterialsResponse {
  lecture_id: number;
  summary: string | null;
  key_points: string[];
  flashcards: Flashcard[];
}

export interface Slide {
  slide_number: number;
  text: string;
}

export interface SlideListResponse {
  lecture_id: number;
  slides: Slide[];
  total: number;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

export interface TranscriptResponse {
  lecture_id: number;
  segments: TranscriptSegment[];
  language?: string | null;
  model?: string | null;
}

export interface TranscriptionResponse {
  lecture_id: number;
  status: string;
  segment_count: number;
  message: string;
}

export interface Course {
  id: number;
  name: string;
  description?: string | null;
  created_at: string;
  lecture_count: number;
  lectures: Lecture[];
  join_code: string;
}

export interface CourseListResponse {
  courses: Course[];
  total: number;
}

export interface CreateCoursePayload {
  name: string;
  description?: string;
}

export interface QueryCluster {
  cluster_id: number;
  count: number;
  questions: string[];
  representative_question: string;
}

export interface QueryClustersResponse {
  clusters: QueryCluster[];
  total_questions: number;
}

export interface TrendPoint {
  period: string;
  count: number;
  questions: string[];
}

export interface TrendsResponse {
  trends: TrendPoint[];
  period: string;
  days: number;
}

export interface LectureHealthMetric {
  lecture_id: number;
  lecture_name: string;
  query_count: number;
  avg_complexity: number;
  top_clusters: Array<{ representative_question: string; count: number }>;
}

export interface LectureHealthResponse {
  lectures: LectureHealthMetric[];
  total_lectures: number;
}

export interface QueryListItem {
  id: number;
  question: string;
  answer: string;
  lecture_id: number | null;
  lecture_name: string | null;
  created_at: string | null;
  user_id?: number | null;
  user_email?: string | null;
}

export interface QueryListResponse {
  queries: QueryListItem[];
  total: number;
}

export interface User {
  id: number;
  email: string;
  role: 'student' | 'instructor';
}

export interface RegisterRequest {
  email: string;
  password: string;
  role?: 'student' | 'instructor';
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// API functions
export const apiClient = {
  // Courses
  async getCourses(): Promise<CourseListResponse> {
    const response = await api.get<CourseListResponse>('/api/courses');
    return response.data;
  },
  async joinCourse(code: string): Promise<{ course_id: number }> {
    const response = await api.post('/api/courses/join', { code });
    return response.data;
  },
  async createCourse(payload: CreateCoursePayload): Promise<Course> {
    const response = await api.post<Course>('/api/courses', payload);
    return response.data;
  },
  async deleteCourse(courseId: number): Promise<void> {
  await api.delete(`/api/courses/${courseId}`);
},

  async addStudentToCourse(courseId: number, email: string): Promise<{ message: string; student_id?: number; student_email: string }> {
    const response = await api.post(`/api/courses/${courseId}/students`, { email });
    return response.data;
  },

  async removeStudentFromCourse(courseId: number, studentId: number): Promise<{ message: string }> {
    const response = await api.delete(`/api/courses/${courseId}/students/${studentId}`);
    return response.data;
  },

  async getCourseStudents(courseId: number): Promise<{ student_id: number; student_email: string }[]> {
    const response = await api.get(`/api/courses/${courseId}/students`);
    return response.data;
  },

  async getCourseAnalytics(courseId: number): Promise<{
    total_questions: number;
    active_students: number;
    top_confused_topics: Array<{ topic: string; count: number; questions?: string[] }>;
    trend_percentage: number;
    trend_direction: string;
  }> {
    const response = await api.get(`/api/courses/${courseId}/analytics`);
    return response.data;
  },

  async queryCourse(courseId: number, question: string, topK: number = 5): Promise<QueryResponse> {
    const response = await api.post<QueryResponse>(
      `/api/courses/${courseId}/query`,
      { question, top_k: topK }
    );
    return response.data;
  },

  async uploadLectureToCourse(courseId: number, file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<UploadResponse>(
      `/api/courses/${courseId}/lectures`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  // Legacy upload endpoint (defaults to general course)
  async uploadLecture(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post<UploadResponse>('/api/lectures/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Lectures
  async getLectures(courseId?: number): Promise<LectureListResponse> {
    const response = await api.get<LectureListResponse>('/api/lectures', {
      params: courseId ? { course_id: courseId } : undefined,
    });
    return response.data;
  },

  async getLecture(id: number): Promise<Lecture> {
    const response = await api.get<Lecture>(`/api/lectures/${id}`);
    return response.data;
  },

  async getLectureStatus(id: number): Promise<{ lecture_id: number; status: string; page_count: number; course_id: number | null }> {
    const response = await api.get(`/api/lectures/${id}/status`);
    return response.data;
  },

  async deleteLecture(id: number): Promise<void> {
    await api.delete(`/api/lectures/${id}`);
  },

  // Queries
  async queryLecture(lectureId: number, question: string, topK: number = 5): Promise<QueryResponse> {
    const response = await api.post<QueryResponse>(
      `/api/lectures/${lectureId}/query`,
      { question, top_k: topK }
    );
    return response.data;
  },

  async getQueryHistory(lectureId: number, limit: number = 20): Promise<QueryHistoryResponse> {
    const response = await api.get<QueryHistoryResponse>(
      `/api/lectures/${lectureId}/history`,
      { params: { limit } }
    );
    return response.data;
  },

  async transcribeLecture(lectureId: number): Promise<TranscriptionResponse> {
    const response = await api.post<TranscriptionResponse>(`/api/lectures/${lectureId}/transcribe`);
    return response.data;
  },

  async getTranscript(lectureId: number): Promise<TranscriptResponse> {
    const response = await api.get<TranscriptResponse>(`/api/lectures/${lectureId}/transcript`);
    return response.data;
  },

  // Study materials
  async getStudyMaterials(lectureId: number): Promise<StudyMaterialsResponse> {
    const response = await api.get<StudyMaterialsResponse>(`/api/lectures/${lectureId}/study-materials`);
    return response.data;
  },

  async getSlides(lectureId: number): Promise<SlideListResponse> {
    const response = await api.get<SlideListResponse>(`/api/lectures/${lectureId}/slides`);
    return response.data;
  },

  async generateSummary(lectureId: number): Promise<SummaryResponse> {
    const response = await api.post<SummaryResponse>(`/api/lectures/${lectureId}/summarize`);
    return response.data;
  },

  async generateKeyPoints(lectureId: number): Promise<KeyPointsResponse> {
    const response = await api.post<KeyPointsResponse>(`/api/lectures/${lectureId}/key-points`);
    return response.data;
  },

  async generateFlashcards(lectureId: number, regenerate: boolean = false): Promise<FlashcardListResponse> {
    if (regenerate) {
      const response = await api.post<FlashcardListResponse>(`/api/lectures/${lectureId}/flashcards/regenerate`);
      return response.data;
    } else {
      const response = await api.post<FlashcardListResponse>(`/api/lectures/${lectureId}/flashcards/generate`);
      return response.data;
    }
  },

  async getLatestFlashcards(lectureId: number): Promise<FlashcardListResponse> {
    const response = await api.get<FlashcardListResponse>(`/api/lectures/${lectureId}/flashcards/latest`);
    return response.data;
  },

  // Instructor analytics
  async getQueryClusters(nClusters: number = 5, lectureId?: number, courseId?: number): Promise<QueryClustersResponse> {
    const params: any = { n_clusters: nClusters };
    if (lectureId !== undefined && lectureId !== null) params.lecture_id = lectureId;
    if (courseId !== undefined && courseId !== null) params.course_id = courseId;
    const response = await api.get<QueryClustersResponse>('/api/instructor/analytics/query-clusters', { params });
    return response.data;
  },

  async getTrends(days: number = 30, groupBy: 'day' | 'week' = 'day', courseId?: number, lectureId?: number): Promise<TrendsResponse> {
    const params: any = { days, group_by: groupBy };
    if (courseId !== undefined && courseId !== null) params.course_id = courseId;
    if (lectureId !== undefined && lectureId !== null) params.lecture_id = lectureId;
    const response = await api.get<TrendsResponse>('/api/instructor/analytics/trends', { params });
    return response.data;
  },

  async getLectureHealth(courseId?: number, lectureId?: number): Promise<LectureHealthResponse> {
    const params: any = {};
    if (courseId !== undefined && courseId !== null) params.course_id = courseId;
    if (lectureId !== undefined && lectureId !== null) params.lecture_id = lectureId;
    const response = await api.get<LectureHealthResponse>('/api/instructor/analytics/lecture-health', { params });
    return response.data;
  },

  async getAllQueries(limit: number = 100, lectureId?: number, courseId?: number): Promise<QueryListResponse> {
    const params: any = { limit };
    if (lectureId !== undefined && lectureId !== null) params.lecture_id = lectureId;
    if (courseId !== undefined && courseId !== null) params.course_id = courseId;
    const response = await api.get<QueryListResponse>('/api/instructor/queries', { params });
    return response.data;
  },

  // Authentication
  async register(email: string, password: string, role: 'student' | 'instructor' = 'student'): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/api/auth/register', { email, password, role });
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/api/auth/login', { email, password });
    if (typeof window !== 'undefined') {
      const token = response.data.access_token;
      console.log('[DEBUG] Storing token:', token ? token.substring(0, 20) + '...' : 'null');
      localStorage.setItem('auth_token', token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      // Verify it was stored
      const stored = localStorage.getItem('auth_token');
      console.log('[DEBUG] Token stored:', stored ? stored.substring(0, 20) + '...' : 'null');
    }
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/api/auth/me');
    return response.data;
  },

  logout(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
    }
  },

  getStoredUser(): User | null {
    if (typeof window === 'undefined') return null;
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  isAuthenticated(): boolean {
    if (typeof window === 'undefined') return false;
    return !!localStorage.getItem('auth_token');
  },
};

