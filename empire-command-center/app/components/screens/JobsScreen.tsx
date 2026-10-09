'use client';
import React from 'react';
import JobBoard from '../business/jobs/JobBoard';

interface JobsScreenProps {
  business?: string;
}

export default function JobsScreen({ business }: JobsScreenProps) {
  return (
    <div className="w-full h-full min-h-screen bg-[var(--bg)]" data-jobs-scrollable="true">
      <JobBoard business={business} />
    </div>
  );
}
