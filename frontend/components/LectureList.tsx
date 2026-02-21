'use client';

import { Lecture } from '@/lib/api';
import Link from 'next/link';

interface LectureListProps {
  lectures: Lecture[];
  onDelete?: (id: number) => void;
  activityByLectureId?: Record<number, number>;
  avgQuestions?: number;
}

export default function LectureList({
  lectures,
  onDelete,
  activityByLectureId,
  avgQuestions,
}: LectureListProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'processing';
      case 'failed':
        return 'error';
      default:
        return status;
    }
  };

  const getActivityBadge = (lectureId: number) => {
    if (!activityByLectureId || !avgQuestions || avgQuestions <= 0) {
      return null;
    }
    const count = activityByLectureId[lectureId] ?? 0;
    if (count <= 0) {
      return null;
    }
    if (count < avgQuestions) {
      return {
        label: 'low activity',
        className: 'bg-gray-100 text-gray-700 border border-gray-200',
      };
    }
    if (count < 2 * avgQuestions) {
      return {
        label: 'medium activity',
        className: 'bg-yellow-50 text-yellow-700 border border-yellow-200',
      };
    }
    return {
      label: 'high Q&A',
      className: 'bg-red-50 text-red-700 border border-red-200',
    };
  };

  if (lectures.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-base">No lectures uploaded yet.</p>
        <p className="text-base mt-2">Upload a PDF to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 text-left">
      {lectures.map((lecture) => (
        <div
          key={lecture.id}
          className="flex items-start justify-between gap-4 p-4 bg-white rounded-lg border border-gray-200 hover:border-primary-300 hover:shadow-sm transition-all overflow-hidden"
        >
          <Link
            href={`/lectures/${lecture.id}`}
            className="flex-1 min-w-0 flex items-start space-x-4 cursor-pointer"
          >
            <div className="flex-shrink-0">
              <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                {lecture.file_type === 'audio' ? (
                  <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-2v13" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 9v10m4-6v6m4-4v4m4-2v2" />
                  </svg>
                ) : (
                  <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                )}
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-base font-medium text-gray-900 truncate" title={lecture.original_name}>
                {lecture.original_name}
              </p>
              <p className="text-base text-gray-500 truncate" title={lecture.original_name}>
                {lecture.file_type === 'audio'
                  ? 'Audio lecture'
                  : lecture.file_type === 'slides'
                  ? `${lecture.page_count} slides`
                  : `${lecture.page_count} pages`}{' '}
                • {new Date(lecture.created_at).toLocaleDateString()}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="px-2 py-1 text-sm font-medium rounded-full bg-gray-100 text-gray-700 uppercase whitespace-nowrap">
                  {lecture.file_type}
                </span>
                <span
                  className={`px-2 py-1 text-sm font-medium rounded-full whitespace-nowrap ${getStatusColor(lecture.status)}`}
                >
                  {getStatusLabel(lecture.status)}
                </span>
                {(() => {
                  const badge = getActivityBadge(lecture.id);
                  if (!badge) return null;
                  return (
                    <span
                      className={`px-2 py-1 text-sm font-medium rounded-full whitespace-nowrap ${badge.className}`}
                    >
                      {badge.label}
                    </span>
                  );
                })()}
                {lecture.file_type === 'audio' && lecture.has_transcript && (
                  <span className="px-2 py-1 text-sm font-medium rounded-full bg-blue-50 text-blue-600 whitespace-nowrap">
                    transcript
                  </span>
                )}
              </div>
            </div>
          </Link>
          {onDelete && (
            <button
              onClick={(e) => {
                e.preventDefault();
                if (confirm(`Delete "${lecture.original_name}"?`)) {
                  onDelete(lecture.id);
                }
              }}
              className="p-2 text-gray-400 hover:text-red-600 transition-colors"
              title="Delete lecture"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

