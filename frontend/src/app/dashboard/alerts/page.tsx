'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AlertsPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard/notifications');
  }, [router]);

  return null;
}
