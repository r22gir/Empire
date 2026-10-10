'use client';
import React from 'react';
import JobBoard from '../business/jobs/JobBoard';

interface JobsScreenProps {
  business?: string;
  initialJobId?: string | number | null;
  initialJobTab?: any;
  onCloseJob?: () => void;
}

export default function JobsScreen({ business, initialJobId, initialJobTab, onCloseJob }: JobsScreenProps) {
  return (
    <div className="w-full h-full min-h-screen bg-[var(--bg)]" data-jobs-scrollable="true">
      <JobBoard business={business} initialJobId={initialJobId} initialJobTab={initialJobTab} />
    </div>
  );
}
