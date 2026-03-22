'use client';

import { useEffect, useRef } from 'react';
import {
  Chart,
  BarController,
  BarElement,
  LineController,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from 'chart.js';
import { PlacementComp } from '../types';

Chart.register(BarController, BarElement, LineController, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend);

interface Props {
  data: PlacementComp[];
  animate: boolean;
}

export default function PlacementBarChart({ data, animate }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current || !animate || data.length === 0) return;
    if (chartRef.current) chartRef.current.destroy();

    const sorted = [...data].sort((a, b) => a.year - b.year);
    const labels = sorted.map((d) => String(d.year));
    const isUSD = sorted[0]?.package_currency === 'USD';

    const pkgValues = sorted.map((d) =>
      isUSD ? d.average_package : +(d.average_package / 100000).toFixed(2)
    );
    const rateValues = sorted.map((d) => d.employment_rate_percent || 0);

    const ctx = canvasRef.current.getContext('2d')!;

    chartRef.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: isUSD ? 'Avg Package ($)' : 'Avg Package (LPA)',
            data: pkgValues,
            backgroundColor: '#070642',
            borderRadius: 8,
            borderSkipped: false,
            yAxisID: 'y',
          },
          {
            type: 'line' as any,
            label: 'Employment Rate %',
            data: rateValues,
            borderColor: '#9a3197',
            backgroundColor: 'rgba(154,49,151,0.12)',
            borderWidth: 2.5,
            pointRadius: 6,
            pointBackgroundColor: '#9a3197',
            tension: 0.4,
            fill: true,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 1000, easing: 'easeOutQuart' },
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'top',
            labels: { usePointStyle: true, pointStyle: 'circle', font: { family: 'Plus Jakarta Sans', size: 12 } },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { family: 'Plus Jakarta Sans' } } },
          y: {
            beginAtZero: true,
            position: 'left',
            grid: { color: 'rgba(0,0,0,0.05)' },
            title: { display: true, text: isUSD ? 'Package ($)' : 'Package (LPA)', font: { family: 'Plus Jakarta Sans', size: 11 } },
          },
          y1: {
            beginAtZero: true,
            max: 100,
            position: 'right',
            grid: { drawOnChartArea: false },
            title: { display: true, text: 'Rate %', font: { family: 'Plus Jakarta Sans', size: 11 } },
          },
        },
      },
    });

    return () => { chartRef.current?.destroy(); };
  }, [data, animate]);

  return (
    <div style={{ position: 'relative', height: 300 }}>
      <canvas ref={canvasRef} />
    </div>
  );
}
