'use client';

/**
 * This file is the route entry for the frontend home page.
 * It connects the home route to its page state and UI components.
 */
import { useRouter } from 'next/navigation';
import HomePageView from '@/components/pages/home/HomePageView';
import { useHomePage } from '@/hooks/useHomePage';

export default function Home() {
  const router = useRouter();
  const page = useHomePage(router);

  return <HomePageView page={page} />;
}
