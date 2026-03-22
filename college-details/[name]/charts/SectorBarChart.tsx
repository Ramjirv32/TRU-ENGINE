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
import { SectorPlacement } from '../types';

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

interface Props {
  data: SectorPlacement[];
  animate: boolean;
}

const SECTOR_COLORS = [
  '#070642', '#9a3197', '#e084cd', '#1a56db', '#0694a2',
  '#057a55', '#c27803', '#e02424', '#6875f5', '#ff5a1f',
];

export default function SectorBarChart({ data, animate }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current || !animate || data.length === 0) return;
    if (chartRef.current) chartRef.current.destroy();

    // Deduplicate by sector (take latest year if duplicates)
    const sectorMap = new Map<string, number>();
    data.forEach((d) => {
      const existing = sectorMap.get(d.sector);
      if (!existing || d.year > (data.find(x => x.sector === d.sector && x.percent === existing)?.year ?? 0)) {
        sectorMap.set(d.sector, Number(d.percent) || 0);
      }
    });

    const labels = Array.from(sectorMap.keys());
    const values = Array.from(sectorMap.values());

    const ctx = canvasRef.current.getContext('2d')!;

    chartRef.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Share %',
            data: values,
            backgroundColor: labels.map((_, i) => SECTOR_COLORS[i % SECTOR_COLORS.length]),
            borderRadius: 6,
            borderSkipped: false,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 1000,
          easing: 'easeOutQuart',
          delay: (ctx: { dataIndex: number }) => ctx.dataIndex * 60,
        } as any,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: (c) => ` ${c.raw}%` },
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            max: 100,
            grid: { color: 'rgba(0,0,0,0.04)' },
            ticks: {
              callback: (v) => `${v}%`,
              font: { family: 'Plus Jakarta Sans', size: 12 },
            },
          },
          y: {
            grid: { display: false },
            ticks: { font: { family: 'Plus Jakarta Sans', size: 12 } },
          },
        },
      },
    });

    return () => { chartRef.current?.destroy(); };
  }, [data, animate]);

  const height = Math.max(260, data.length * 44);

  return (
    <div style={{ position: 'relative', height }}>
      <canvas ref={canvasRef} />
    </div>
  );
}
