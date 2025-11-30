'use client'

import React, { useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { useConsiderBuying } from '@/lib/queries'
import { Suspense } from 'react'

function DebugConsideringContent() {
  const searchParams = useSearchParams()
  const user = searchParams.get('user') || 'peichin'
  const status = searchParams.get('status') || 'considering'

  const { 
    data, 
    isLoading, 
    isError, 
    error, 
    isFetching,
    isSuccess,
    dataUpdatedAt,
    status: queryStatus
  } = useConsiderBuying(user, status)

  // Log to console for debugging
  useEffect(() => {
    console.log('Debug Considering Hook State:', {
      user,
      status,
      isLoading,
      isFetching,
      isError,
      isSuccess,
      queryStatus,
      data,
      error
    })
  }, [user, status, isLoading, isFetching, isError, isSuccess, queryStatus, data, error])

  // Test direct API call
  useEffect(() => {
    const testDirectCall = async () => {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const url = `${API_URL}/api/consider-buying/list?user_id=${user}&status=${status}`
      console.log('Testing direct API call to:', url)
      try {
        const res = await fetch(url)
        console.log('Direct API call response status:', res.status)
        const json = await res.json()
        console.log('Direct API call response data:', json)
      } catch (err) {
        console.error('Direct API call error:', err)
      }
    }
    testDirectCall()
  }, [user, status])

  return (
    <div className="min-h-screen bg-white p-8">
      <h1 className="text-2xl font-bold mb-4">React Query Diagnostic: Considering Items</h1>
      
      <div className="space-y-4">
        <div className="bg-gray-100 p-4 rounded">
          <h2 className="font-semibold mb-2">Query Parameters</h2>
          <p>User: <code className="bg-white px-2 py-1 rounded">{user}</code></p>
          <p>Status: <code className="bg-white px-2 py-1 rounded">{status}</code></p>
        </div>

        <div className="bg-blue-50 p-4 rounded border border-blue-200">
          <h2 className="font-semibold mb-2">Query State</h2>
          <ul className="space-y-1 text-sm">
            <li>Query Status: <code className="bg-white px-2 py-1 rounded">{queryStatus}</code></li>
            <li>isLoading: <code className="bg-white px-2 py-1 rounded">{isLoading ? 'true' : 'false'}</code></li>
            <li>isFetching: <code className="bg-white px-2 py-1 rounded">{isFetching ? 'true' : 'false'}</code></li>
            <li>isSuccess: <code className="bg-white px-2 py-1 rounded">{isSuccess ? 'true' : 'false'}</code></li>
            <li>isError: <code className="bg-white px-2 py-1 rounded">{isError ? 'true' : 'false'}</code></li>
            <li>Data Updated At: <code className="bg-white px-2 py-1 rounded">{dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleString() : 'N/A'}</code></li>
          </ul>
        </div>

        {isError && (
          <div className="bg-red-50 p-4 rounded border border-red-200">
            <h2 className="font-semibold mb-2 text-red-800">Error</h2>
            <pre className="bg-white p-2 rounded text-xs overflow-auto">
              {error ? JSON.stringify(error, null, 2) : 'Unknown error'}
            </pre>
          </div>
        )}

        <div className="bg-green-50 p-4 rounded border border-green-200">
          <h2 className="font-semibold mb-2">Response Data</h2>
          {data ? (
            <div>
              <p className="mb-2">
                Data Type: <code className="bg-white px-2 py-1 rounded">{typeof data}</code>
              </p>
              <p className="mb-2">
                Has "items" key: <code className="bg-white px-2 py-1 rounded">{data.items ? 'true' : 'false'}</code>
              </p>
              <p className="mb-2">
                Items Count: <code className="bg-white px-2 py-1 rounded">{data.items?.length || 0}</code>
              </p>
              <p className="mb-2">
                Data Keys: <code className="bg-white px-2 py-1 rounded">{data ? Object.keys(data).join(', ') : 'N/A'}</code>
              </p>
              
              {data.items && data.items.length > 0 && (
                <div className="mt-4">
                  <h3 className="font-semibold mb-2">First Item Structure:</h3>
                  <pre className="bg-white p-2 rounded text-xs overflow-auto max-h-60">
                    {JSON.stringify(data.items[0], null, 2)}
                  </pre>
                </div>
              )}

              <div className="mt-4">
                <h3 className="font-semibold mb-2">Full Response:</h3>
                <pre className="bg-white p-2 rounded text-xs overflow-auto max-h-96">
                  {JSON.stringify(data, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <p className="text-gray-600">No data yet</p>
          )}
        </div>

        <div className="bg-yellow-50 p-4 rounded border border-yellow-200">
          <h2 className="font-semibold mb-2">Raw Data (for debugging)</h2>
          <pre className="bg-white p-2 rounded text-xs overflow-auto">
            {JSON.stringify({ data, isLoading, isError, error, queryStatus }, null, 2)}
          </pre>
        </div>

        <div className="bg-purple-50 p-4 rounded border border-purple-200">
          <h2 className="font-semibold mb-2">Expected vs Actual</h2>
          <ul className="space-y-1 text-sm">
            <li>Expected Items: <code className="bg-white px-2 py-1 rounded">34</code></li>
            <li>Actual Items: <code className="bg-white px-2 py-1 rounded">{data?.items?.length || 0}</code></li>
            <li>Match: <code className="bg-white px-2 py-1 rounded">{data?.items?.length === 34 ? '✅ YES' : '❌ NO'}</code></li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default function DebugConsideringPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading diagnostic page...</div>}>
      <DebugConsideringContent />
    </Suspense>
  )
}

