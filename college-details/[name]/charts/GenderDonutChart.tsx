'use client';

import { useEffect, useRef } from 'react';
import {
  Chart,
  ArcElement,
  DoughnutController,
  Tooltip,
  Legend,
} from 'chart.js';

Chart.register(ArcElement, DoughnutController, Tooltip, Legend);

interface Props {
  male: number;
  female: number;
  animate: boolean;
  /** compact = smaller cutout, used in placements gender section */
  compact?: boolean;
  label?: string;
  value?: string;
}

export default function GenderDonutChart({ male, female, animate, compact = false, label = 'Female', value }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current || !animate) return;
    if (chartRef.current) chartRef.current.destroy();

    const ctx = canvasRef.current.getContext('2d')!;

    chartRef.current = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Male', 'Female'],
        datasets: [
          {
            data: [male || 50, female || 50],
            backgroundColor: ['#070642', '#9a3197'],
            hoverBackgroundColor: ['#1a1a6e', '#b83db5'],
            borderWidth: 0,
            hoverOffset: 10,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: compact ? '65%' : '78%',
        animation: { animateRotate: true, duration: 1000, easing: 'easeOutQuart' },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: (c) => ` ${c.label}: ${c.raw}%` },
          },
        },
      },
    });

    return () => { chartRef.current?.destroy(); };
  }, [male, female, animate, compact]);

  const displayValue = value ?? `${female}%`;

  return (
    <div style={{ position: 'relative', width: '100%', height: compact ? 140 : 190 }}>
      <canvas ref={canvasRef} />
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)', textAlign: 'center', pointerEvents: 'none',
      }}>
        <span style={{ fontSize: compact ? 18 : 26, fontWeight: 800, color: '#9a3197', display: 'block', lineHeight: 1 }}>
          {displayValue}
        </span>
        <span style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>{label}</span>
      </div>
    </div>
  );
}
