"use client";

import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';

interface JobExecution {
  id: string;
  job_type: string;
  status: string;
  progress: number;
  error_message?: string;
}

export function JobPollingWidget({ jobId, onComplete }: { jobId: string, onComplete: () => void }) {
  const [job, setJob] = useState<JobExecution | null>(null);

  useEffect(() => {
    let interval: NodeJS.Timeout;

    const pollJob = async () => {
      // In a real app we fetch from /api/v1/jobs/{jobId}
      // For this implementation, we will simulate the polling
      setJob(prev => {
        if (!prev) return { id: jobId, job_type: 'COMPLIANCE_RUN', status: 'RUNNING', progress: 10 };
        
        let nextProgress = prev.progress + 25;
        if (nextProgress >= 100) {
          clearInterval(interval);
          onComplete();
          // We can dispatch a custom event or let the parent handle the toast
          return { ...prev, status: 'COMPLETED', progress: 100 };
        }
        return { ...prev, progress: nextProgress };
      });
    };

    interval = setInterval(pollJob, 1000);
    return () => clearInterval(interval);
  }, [jobId, onComplete]);

  if (!job) return null;

  return (
    <div className="mb-4 bg-slate-50 border border-blue-200 rounded-lg p-4 flex items-center gap-4">
      {job.status === 'RUNNING' || job.status === 'PENDING' ? (
        <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
      ) : job.status === 'COMPLETED' ? (
        <CheckCircle className="h-6 w-6 text-green-500" />
      ) : (
        <AlertCircle className="h-6 w-6 text-red-500" />
      )}
      
      <div className="flex-1 space-y-2">
        <div className="flex justify-between text-sm font-medium">
          <span className="text-slate-700">Executing: {job.job_type.replace('_', ' ')}</span>
          <span className="text-slate-700">{job.progress}%</span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-2">
          <div className="bg-blue-600 h-2 rounded-full transition-all duration-500" style={{ width: `${job.progress}%` }}></div>
        </div>
        {job.error_message && <p className="text-xs text-red-500 mt-1">{job.error_message}</p>}
      </div>
    </div>
  );
}
