'use client';

import { useEffect, useRef } from 'react';
import {
  Chart,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from 'chart.js';
import { FeesYearInfo } from '../types';

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

interface Props {
  data: any[]; // Can be FeesYearInfo or simple { course, year_1, total }
  animate: boolean;
}

export default function FeesBarChart({ data, animate }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current || !animate || data.length === 0) return;
    if (chartRef.current) chartRef.current.destroy();

    // Support both formats
    const labels = data.map(d => d.course || d.program_type || d.year || 'Course');
    const values = data.map(d => {
        const val = d.year_1 || d.per_year || d.per_year_local;
        return typeof val === 'number' ? val : parseFloat(String(val).replace(/[^0-9.]/g, '')) || 0;
    });

    const ctx = canvasRef.current.getContext('2d')!;

    chartRef.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Fee (Per Year)',
            data: values,
            backgroundColor: 'rgba(129, 140, 248, 0.8)',
            borderColor: 'rgba(129, 140, 248, 1)',
            borderWidth: 1,
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 1000, easing: 'easeOutQuart' },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                let label = context.dataset.label || '';
                if (label) label += ': ';
                if (context.parsed.y !== null) {
                  label += new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(context.parsed.y);
                }
                return label;
              }
            }
          }
        },
        scales: {
          x: { 
            grid: { display: false },
            ticks: { 
                font: { family: 'Plus Jakarta Sans', size: 10 },
                maxRotation: 45,
                minRotation: 45
            } 
          },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: {
              callback: (value) => {
                if (Number(value) >= 100000) return (Number(value) / 100000).toFixed(1) + 'L';
                if (Number(value) >= 1000) return (Number(value) / 1000).toFixed(0) + 'K';
                return value;
              }
            }
          },
        },
      },
    });

    return () => {
      if (chartRef.current) chartRef.current.destroy();
    };
  }, [data, animate]);

  return (
    <div style={{ height: '300px', width: '100%', position: 'relative' }}>
        <canvas ref={canvasRef} />
    </div>
  );
}
