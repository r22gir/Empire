'use client';
import React from 'react';
import Link from 'next/link';

export default function PetForgePage() {
  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#f5f3ef',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
    }}>
      <div style={{
        textAlign: 'center',
        maxWidth: '560px',
      }}>
        <div style={{
          width: '80px',
          height: '80px',
          borderRadius: '50%',
          backgroundColor: '#fef2f2',
          border: '3px solid #b8960c',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1.5rem',
          fontSize: '2.25rem',
        }}>
          🐾
        </div>

        <h1 style={{
          fontSize: '2.5rem',
          fontWeight: 700,
          color: '#1a1a1a',
          margin: '0 0 0.5rem',
          letterSpacing: '-0.02em',
        }}>
          PetForge
        </h1>

        <p style={{
          fontSize: '1.125rem',
          fontWeight: 500,
          color: '#b8960c',
          margin: '0 0 1.5rem',
        }}>
          Coming Soon &mdash; Empire v6.0
        </p>

        <p style={{
          fontSize: '1rem',
          color: '#555',
          lineHeight: 1.7,
          margin: '0 0 2.5rem',
        }}>
          A complete veterinary clinic management platform &mdash; patient records,
          appointment scheduling, prescriptions, billing, and an owner-facing pet
          portal, all powered by the Empire AI engine.
        </p>

        <Link
          href="/"
          style={{
            display: 'inline-block',
            padding: '0.75rem 2rem',
            backgroundColor: '#b8960c',
            color: '#fff',
            fontWeight: 600,
            fontSize: '0.95rem',
            borderRadius: '8px',
            textDecoration: 'none',
            transition: 'opacity 0.2s',
          }}
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
