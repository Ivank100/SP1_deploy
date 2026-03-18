'use client';

/**
 * This file is the Next.js route entry for the auth/register page.
 * It connects route parameters and page-level wiring to the matching view logic.
 */
import { useRouter } from 'next/navigation';
import RegisterPageView from '@/components/pages/auth/RegisterPageView';
import { useRegisterPage } from '@/hooks/useRegisterPage';

export default function RegisterPage() {
  const router = useRouter();
  const page = useRegisterPage(router);

  return <RegisterPageView page={page} />;
}
