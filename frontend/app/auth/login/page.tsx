'use client';

/**
 * This file is the Next.js route entry for the auth/login page.
 * It connects route parameters and page-level wiring to the matching view logic.
 */
import { useRouter } from 'next/navigation';
import LoginPageView from '@/components/pages/auth/LoginPageView';
import { useLoginPage } from '@/hooks/useLoginPage';

export default function LoginPage() {
  const router = useRouter();
  const page = useLoginPage(router);

  return <LoginPageView page={page} />;
}
