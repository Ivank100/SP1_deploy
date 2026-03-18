'use client';

import { useParams, useRouter } from 'next/navigation';
import LecturePageContent from '@/components/lectures/LecturePageContent';
import { apiClient } from '@/lib/api';
import { useLectureQuestions } from '@/hooks/useLectureQuestions';
import { useLectureWorkspace } from '@/hooks/useLectureWorkspace';

export default function LecturePage() {
  const params = useParams();
  const router = useRouter();
  const lectureId = parseInt(params.id as string, 10);

  const workspace = useLectureWorkspace(lectureId, router);
  const questions = useLectureQuestions(lectureId, workspace.currentUser);

  return (
    <LecturePageContent
      workspace={workspace}
      questions={questions}
      onLogout={() => {
        apiClient.logout();
        router.push('/auth/login');
      }}
    />
  );
}
