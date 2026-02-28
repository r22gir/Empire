'use client';
import { useMemo } from 'react';
import { Brain, Sparkles, Eye } from 'lucide-react';

export type AvatarState = 'idle' | 'thinking' | 'speaking' | 'presenting' | 'done';

interface Props {
  state: AvatarState;
  size?: 'sm' | 'md' | 'lg';
}

export default function AvatarDisplay({ state, size = 'md' }: Props) {
  const dims = useMemo(() => {
    switch (size) {
      case 'sm': return { container: 32, icon: 14, ring: 36 };
      case 'lg': return { container: 64, icon: 28, ring: 70 };
      default:   return { container: 48, icon: 20, ring: 54 };
    }
  }, [size]);

  const stateClass = useMemo(() => {
    switch (state) {
      case 'thinking':   return 'avatar-thinking';
      case 'speaking':   return 'avatar-speaking';
      case 'presenting': return 'avatar-presenting';
      case 'done':       return 'avatar-done';
      default:           return 'avatar-idle';
    }
  }, [state]);

  return (
    <div className={`avatar-display ${stateClass}`} style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
      {/* Outer ring pulse */}
      <div
        className="avatar-ring"
        style={{
          position: 'absolute',
          width: dims.ring,
          height: dims.ring,
          borderRadius: '50%',
          border: '2px solid var(--gold)',
          opacity: state === 'idle' ? 0.15 : 0.4,
          animation: state === 'thinking' ? 'avatar-pulse 1.2s ease-in-out infinite' :
                     state === 'speaking' ? 'avatar-pulse 0.8s ease-in-out infinite' :
                     state === 'presenting' ? 'avatar-glow 2s ease-in-out infinite' :
                     'none',
        }}
      />

      {/* Main avatar circle */}
      <div
        style={{
          width: dims.container,
          height: dims.container,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #D4AF37 0%, #8B5CF6 50%, #D946EF 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          boxShadow: state === 'speaking' ? '0 0 20px rgba(212,175,55,0.4)' :
                     state === 'thinking' ? '0 0 15px rgba(139,92,246,0.3)' :
                     '0 0 8px rgba(212,175,55,0.15)',
          transition: 'box-shadow 0.3s ease',
        }}
      >
        {/* Icon based on state */}
        {state === 'thinking' ? (
          <Eye className="text-white" style={{ width: dims.icon, height: dims.icon, animation: 'avatar-eye-scan 2s ease-in-out infinite' }} />
        ) : state === 'presenting' ? (
          <Sparkles className="text-white" style={{ width: dims.icon, height: dims.icon, animation: 'avatar-sparkle 1.5s ease-in-out infinite' }} />
        ) : (
          <Brain className="text-white" style={{ width: dims.icon, height: dims.icon }} />
        )}

        {/* Speaking mouth indicator */}
        {state === 'speaking' && (
          <div
            style={{
              position: 'absolute',
              bottom: size === 'sm' ? 4 : size === 'lg' ? 12 : 8,
              left: '50%',
              transform: 'translateX(-50%)',
              display: 'flex',
              gap: 1.5,
              alignItems: 'flex-end',
            }}
          >
            {[0, 1, 2].map(i => (
              <div
                key={i}
                style={{
                  width: size === 'sm' ? 2 : 3,
                  background: 'white',
                  borderRadius: 1,
                  animation: `avatar-speak-bar 0.6s ease-in-out ${i * 0.15}s infinite`,
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Status dot */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          right: 0,
          width: size === 'sm' ? 8 : 10,
          height: size === 'sm' ? 8 : 10,
          borderRadius: '50%',
          background: state === 'thinking' ? 'var(--purple)' :
                      state === 'speaking' ? 'var(--gold)' :
                      state === 'presenting' ? '#D946EF' :
                      '#22c55e',
          border: '2px solid var(--void)',
          animation: state !== 'idle' && state !== 'done' ? 'pulse-online 1.5s infinite' : 'none',
        }}
      />

      <style jsx>{`
        @keyframes avatar-pulse {
          0%, 100% { transform: scale(1); opacity: 0.3; }
          50% { transform: scale(1.15); opacity: 0.6; }
        }
        @keyframes avatar-glow {
          0%, 100% { box-shadow: 0 0 10px rgba(217,70,239,0.2); opacity: 0.3; }
          50% { box-shadow: 0 0 25px rgba(217,70,239,0.5); opacity: 0.6; }
        }
        @keyframes avatar-eye-scan {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-2px) translateY(-1px); }
          75% { transform: translateX(2px) translateY(1px); }
        }
        @keyframes avatar-sparkle {
          0%, 100% { transform: scale(1) rotate(0deg); }
          50% { transform: scale(1.1) rotate(10deg); }
        }
        @keyframes avatar-speak-bar {
          0%, 100% { height: 2px; }
          50% { height: ${size === 'sm' ? 5 : 8}px; }
        }
      `}</style>
    </div>
  );
}
