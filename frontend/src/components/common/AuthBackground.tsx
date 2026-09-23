import type { CSSProperties } from 'react';

// Fixed layout (not random) so the pattern is identical on every visit and between login/register.
// left/bottom are % of the bottom-half area; size in px; delay/duration in seconds; drift = sideways px.
const BUBBLES: Array<{ left: number; bottom: number; size: number; delay: number; duration: number; drift: number; tone: 'blue' | 'violet' }> = [
  { left: 6, bottom: 10, size: 90, delay: 0, duration: 11, drift: 30, tone: 'blue' },
  { left: 18, bottom: 45, size: 44, delay: 3, duration: 9, drift: -20, tone: 'violet' },
  { left: 30, bottom: 5, size: 130, delay: 6, duration: 14, drift: 40, tone: 'blue' },
  { left: 44, bottom: 35, size: 60, delay: 1.5, duration: 10, drift: -35, tone: 'violet' },
  { left: 57, bottom: 12, size: 100, delay: 8, duration: 13, drift: 25, tone: 'blue' },
  { left: 68, bottom: 50, size: 38, delay: 4.5, duration: 8, drift: 20, tone: 'blue' },
  { left: 78, bottom: 20, size: 120, delay: 2, duration: 15, drift: -40, tone: 'violet' },
  { left: 90, bottom: 40, size: 56, delay: 7, duration: 10, drift: -25, tone: 'blue' },
];

/** Decorative, slowly drifting circles that fade in and out across the bottom half of the auth pages. */
export default function AuthBackground() {
  return (
    <div className="auth-bubbles" aria-hidden="true">
      {BUBBLES.map((bubble, index) => (
        <span
          key={index}
          className={`auth-bubble auth-bubble-${bubble.tone}`}
          style={
            {
              left: `${bubble.left}%`,
              bottom: `${bubble.bottom}%`,
              width: bubble.size,
              height: bubble.size,
              animationDelay: `${bubble.delay}s`,
              animationDuration: `${bubble.duration}s`,
              '--drift': `${bubble.drift}px`,
            } as CSSProperties
          }
        />
      ))}
    </div>
  );
}
