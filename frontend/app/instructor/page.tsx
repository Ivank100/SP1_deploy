'use client';

/**
 * This file is the Next.js route entry for the instructor page.
 * It connects route parameters and page-level wiring to the matching view logic.
 */
import { useRouter } from 'next/navigation';
import InstructorDashboardPageView from '@/components/pages/instructor/InstructorDashboardPageView';
import { useInstructorDashboardPage } from '@/hooks/useInstructorDashboardPage';

export default function InstructorDashboard() {
  const router = useRouter();
  const page = useInstructorDashboardPage(router);

  return <InstructorDashboardPageView page={page} />;
}
