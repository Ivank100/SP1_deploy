'use client';

/**
 * This hook manages state and actions for the authenticated user workflow.
 * It loads data, tracks UI state, and returns handlers used by page components.
 */
import { useEffect, useState } from 'react';
import { apiClient, User } from '@/lib/api';

type RouterLike = {
  push: (href: string) => void;
};

export function useAuthenticatedUser(router: RouterLike) {
  const [user, setUser] = useState<User | null>(() => apiClient.getStoredUser());

  useEffect(() => {
    if (!apiClient.isAuthenticated()) {
      setUser(null);
      router.push('/auth/login');
      return;
    }

    const storedUser = apiClient.getStoredUser();
    if (storedUser) {
      setUser(storedUser);
      return;
    }

    apiClient
      .getCurrentUser()
      .then(setUser)
      .catch(() => {
        apiClient.logout();
        setUser(null);
        router.push('/auth/login');
      });
  }, [router]);

  return { user, setUser };
}
