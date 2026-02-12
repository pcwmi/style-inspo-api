import { cookies } from 'next/headers'
import { ShowcaseLanding } from '@/components/ShowcaseLanding'
import { DashboardClient } from '@/components/DashboardClient'
import { Suspense } from 'react'

export default function Page({ searchParams }: { searchParams: { user?: string } }) {
  const userParam = searchParams.user
  const sessionCookie = cookies().get('session')

  // No user param and no session → landing page (instant, server-rendered)
  if (!userParam && !sessionCookie) {
    return <ShowcaseLanding />
  }

  // Has user param or session → client-side dashboard
  return (
    <Suspense fallback={<div className="min-h-screen bg-bone" />}>
      <DashboardClient />
    </Suspense>
  )
}
