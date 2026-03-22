'use client';

import { useEffect, useRef } from 'react';
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import { StudentCountEntry } from '../types';

Chart.register(LineController, LineElement, PointElement, CategoryScale, LinearScale, Filler, Tooltip, Legend);

interface Props {
  data: StudentCountEntry[];
  animate: boolean;
}

export default function EnrollmentAreaChart({ data, animate }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current || !animate || data.length === 0) return;
    if (chartRef.current) chartRef.current.destroy();

    const sorted = [...data].sort((a, b) => a.year - b.year);
    const labels = sorted.map((d) => String(d.year));

    const ctx = canvasRef.current.getContext('2d')!;

    // Build gradients
    const makeGrad = (c1: string, c2: string) => {
      const g = ctx.createLinearGradient(0, 0, 0, 300);
      g.addColorStop(0, c1);
      g.addColorStop(1, c2);
      return g;
    };

    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'UG',
            data: sorted.map((d) => d.ug),
            borderColor: '#070642',
            backgroundColor: makeGrad('rgba(7,6,66,0.25)', 'rgba(7,6,66,0.02)'),
            fill: true,
            tension: 0.45,
            borderWidth: 2.5,
            pointRadius: 5,
            pointBackgroundColor: '#070642',
          },
          {
            label: 'PG',
            data: sorted.map((d) => d.pg),
            borderColor: '#9a3197',
            backgroundColor: makeGrad('rgba(154,49,151,0.22)', 'rgba(154,49,151,0.02)'),
            fill: true,
            tension: 0.45,
            borderWidth: 2.5,
            pointRadius: 5,
            pointBackgroundColor: '#9a3197',
          },
          {
            label: 'PhD',
            data: sorted.map((d) => d.phd),
            borderColor: '#e084cd',
            backgroundColor: makeGrad('rgba(224,132,205,0.2)', 'rgba(224,132,205,0.02)'),
            fill: true,
            tension: 0.45,
            borderWidth: 2.5,
            pointRadius: 5,
            pointBackgroundColor: '#e084cd',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 1100, easing: 'easeOutQuart' },
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'top',
            labels: { usePointStyle: true, pointStyle: 'circle', font: { family: 'Plus Jakarta Sans', size: 12 } },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.dataset.label}: ${Number(ctx.raw).toLocaleString()}`,
            },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { family: 'Plus Jakarta Sans', size: 12 } } },
          y: {
            beginAtZero: false,
            grid: { color: 'rgba(0,0,0,0.05)' },
            ticks: {
              font: { family: 'Plus Jakarta Sans', size: 12 },
              callback: (v) => Number(v).toLocaleString(),
            },
          },
        },
      },
    });

    return () => { chartRef.current?.destroy(); };
  }, [data, animate]);

  return (
    <div style={{ position: 'relative', height: 280 }}>
      <canvas ref={canvasRef} />
    </div>
  );
}
