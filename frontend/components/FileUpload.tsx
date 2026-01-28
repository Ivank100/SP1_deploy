'use client';

import { useState, useRef } from 'react';
import { apiClient } from '@/lib/api';

interface FileUploadProps {
  courseId: number | null;
  onUploadSuccess: () => void;
  mode?: 'direct' | 'request';
}

export default function FileUpload({ courseId, onUploadSuccess, mode = 'direct' }: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!courseId) {
      setError('Please select a course before uploading.');
      return;
    }

    const extension = file.name.split('.').pop()?.toLowerCase();
    const allowedExtensions = ['pdf', 'mp3', 'wav', 'm4a', 'ppt', 'pptx'];
    if (!extension || !allowedExtensions.includes(extension)) {
      setError('Please upload a PDF or audio file (MP3, WAV, M4A)');
      return;
    }

    // Validate file size (50MB)
    if (file.size > 50 * 1024 * 1024) {
      setError('File size must be less than 50MB');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      if (mode === 'request') {
        await apiClient.requestUploadToCourse(courseId, file);
      } else {
        await apiClient.uploadLectureToCourse(courseId, file);
      }
      onUploadSuccess();
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.mp3,.wav,.m4a,.ppt,.pptx,audio/*,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/vnd.ms-powerpoint"
        onChange={handleFileSelect}
        className="hidden"
        id="file-upload"
        disabled={uploading || !courseId}
      />
      <label
        htmlFor="file-upload"
        className={`
          flex items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer
          transition-colors duration-200
          ${(uploading || !courseId) 
            ? 'border-gray-300 bg-gray-50 cursor-not-allowed' 
            : 'border-gray-300 hover:border-primary-500 hover:bg-primary-50'
          }
        `}
      >
        <div className="flex flex-col items-center justify-center pt-5 pb-6">
          {uploading ? (
            <>
              <svg className="w-8 h-8 mb-2 text-primary-500 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
              <p className="text-sm text-gray-600">
                {mode === 'request' ? 'Submitting for approval...' : 'Uploading and processing...'}
              </p>
            </>
          ) : (
            <>
              <svg className="w-8 h-8 mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="mb-2 text-sm text-gray-500">
                {courseId ? (
                  <>
                    <span className="font-semibold">
                      {mode === 'request' ? 'Click to submit' : 'Click to upload'}
                    </span>{' '}
                    or drag and drop
                  </>
                ) : (
                  'Select a course to enable uploads'
                )}
              </p>
              <p className="text-xs text-gray-500">
                {mode === 'request'
                  ? 'PDF, audio, or slides (pending approval)'
                  : 'PDF, audio, or slides (MAX. 50MB)'}
              </p>
            </>
          )}
        </div>
      </label>
      {error && (
        <div className="mt-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
          {error}
        </div>
      )}
    </div>
  );
}

