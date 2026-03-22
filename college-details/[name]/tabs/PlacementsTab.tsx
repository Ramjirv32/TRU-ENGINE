'use client';

import dynamic from 'next/dynamic';
import {
  TrendingUp, Users, Building2, Award, BarChart2,
  Briefcase, DollarSign, PercentCircle, UserCheck,
} from 'lucide-react';
import { CollegeData, formatPackage, formatValue } from '../types';
import { useInView, useCountUp } from '../hooks';

const PlacementBarChart = dynamic(() => import('../charts/PlacementBarChart'), { ssr: false });
const SectorBarChart = dynamic(() => import('../charts/SectorBarChart'), { ssr: false });
const GenderDonutChart = dynamic(() => import('../charts/GenderDonutChart'), { ssr: false });

interface Props { college: CollegeData }

// ─── animated KPI card ────────────────────────────────────────────────────
function KpiCard({
  icon, rawValue, displayValue, label, accent = false, active,
}: {
  icon: React.ReactNode; rawValue: number; displayValue: string;
  label: string; accent?: boolean; active: boolean;
}) {
  // count-up only makes sense for pure numbers; otherwise skip
  const counted = useCountUp(rawValue, active);
  const show = rawValue > 0 ? counted.toLocaleString() : displayValue;

  return (
    <div className={`kpi-card ${accent ? 'kpi-card--accent' : ''}`}>
      <div className="kpi-card-icon">{icon}</div>
      <span className="kpi-card-value">
        {rawValue > 0 && active ? (
          // For package values we switch to formatted once count-up nears
          displayValue !== String(rawValue) ? displayValue : show
        ) : displayValue}
      </span>
      <span className="kpi-card-label">{label}</span>
    </div>
  );
}

function SectionTitle({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <h2 className="section-title">
      <span className="section-icon">{icon}</span>
      {children}
    </h2>
  );
}

// ─── animated horizontal progress bar ────────────────────────────────────
function ProgressBar({ label, value, color, active }: { label: string; value: number; color: string; active: boolean }) {
  return (
    <div className="prog-row">
      <div className="prog-meta">
        <span className="prog-label">{label}</span>
        <span className="prog-pct" style={{ color }}>{value}%</span>
      </div>
      <div className="prog-track">
        <div
          className="prog-fill"
          style={{
            width: active ? `${value}%` : '0%',
            background: color,
            transition: active ? 'width 1.2s ease-out' : 'none',
          }}
        />
      </div>
    </div>
  );
}

// deterministic color from company name
const LOGO_COLORS = ['#070642', '#9a3197', '#1a56db', '#057a55', '#c27803', '#0694a2', '#e02424', '#6875f5'];
function logoColor(name: string) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
  return LOGO_COLORS[Math.abs(h) % LOGO_COLORS.length];
}

export default function PlacementsTab({ college }: Props) {
  const kpiView = useInView();
  const trendView = useInView();
  const sectorView = useInView();
  const genderView = useInView();
  const recruiterView = useInView();

  const pd = college.placements_data;
  const pl = pd?.placements || college.placements;
  const iso = pl?.package_currency === 'USD';

  // ─── Employment rate mini-doughnuts ───────────────────────────────────
  const compData = pd?.placement_comparison_last_3_years || college.placement_comparison_last_3_years || [];
  const genderPl = pd?.gender_based_placement_last_3_years || college.gender_based_placement_last_3_years || [];
  const sectors = pd?.sector_wise_placement_last_3_years || college.sector_wise_placement_last_3_years || [];
  const recruiters = pd?.top_recruiters || college.top_recruiters || [];
  const highlights = pd?.placement_highlights || college.placement_highlights;

  return (
    <div className="tab-content">

      {/* ── KPI Row ──────────────────────────────────────────────────── */}
      {pl && (pl.highest_package > 0 || pl.total_students_placed > 0) && (
        <section className="content-section">
          <SectionTitle icon={<Award size={20} />}>
            Placement Statistics{pl.year ? ` (${pl.year})` : ''}
          </SectionTitle>
          <div ref={kpiView.ref} className="kpi-grid">
            <KpiCard
              icon={<DollarSign size={20} />}
              rawValue={pl.highest_package}
              displayValue={formatPackage(pl.highest_package, pl.package_currency)}
              label="Highest Package"
              accent active={kpiView.inView}
            />
            <KpiCard
              icon={<TrendingUp size={20} />}
              rawValue={pl.average_package}
              displayValue={formatPackage(pl.average_package, pl.package_currency)}
              label="Average Package"
              active={kpiView.inView}
            />
            <KpiCard
              icon={<BarChart2 size={20} />}
              rawValue={pl.median_package}
              displayValue={formatPackage(pl.median_package, pl.package_currency)}
              label="Median Package"
              active={kpiView.inView}
            />
            <KpiCard
              icon={<PercentCircle size={20} />}
              rawValue={pl.placement_rate_percent}
              displayValue={pl.placement_rate_percent ? `${pl.placement_rate_percent}%` : '-'}
              label="Placement Rate"
              accent active={kpiView.inView}
            />
            <KpiCard
              icon={<UserCheck size={20} />}
              rawValue={pl.total_students_placed}
              displayValue={pl.total_students_placed ? pl.total_students_placed.toLocaleString() : '-'}
              label="Students Placed"
              active={kpiView.inView}
            />
            <KpiCard
              icon={<Building2 size={20} />}
              rawValue={pl.total_companies_visited}
              displayValue={pl.total_companies_visited ? pl.total_companies_visited.toLocaleString() : '-'}
              label="Companies Visited"
              active={kpiView.inView}
            />
          </div>
        </section>
      )}

      {/* ── Highlights / Notes ────────────────────────────────────── */}
      {highlights && (
        <section className="content-section">
          <div className="info-callout">
            <TrendingUp size={15} style={{ marginRight: 8, flexShrink: 0 }} />
            <div>
              <strong>Highlights</strong><br />
              {highlights}
            </div>
          </div>
        </section>
      )}
      {pl?.graduate_outcomes_note && (
        <section className="content-section">
          <div className="info-callout info-callout--muted">
            <Award size={15} style={{ marginRight: 8, flexShrink: 0 }} />
            <div>
              <strong>Graduate Outcomes</strong><br />
              {pl.graduate_outcomes_note}
            </div>
          </div>
        </section>
      )}

      {/* ── 3-Year Placement Trend ────────────────────────────────── */}
      {compData.length > 0 && (
        <section className="content-section">
          <SectionTitle icon={<TrendingUp size={20} />}>Placement Trend (Last 3 Years)</SectionTitle>
          <div ref={trendView.ref} className="chart-card-full">
            <PlacementBarChart data={compData} animate={trendView.inView} />
          </div>

          {/* Employment rate mini-donut row */}
          <div className="emp-rate-row" style={{ marginTop: 24 }}>
            {compData.map((c) => (
              <div key={c.year} className="emp-rate-item">
                <GenderDonutChart
                  male={100 - (c.employment_rate_percent || 0)}
                  female={c.employment_rate_percent || 0}
                  animate={trendView.inView}
                  compact
                  label="Employment"
                  value={`${c.employment_rate_percent ?? 0}%`}
                />
                <span className="emp-rate-year">{c.year}</span>
              </div>
            ))}
          </div>

          <table className="data-table" style={{ marginTop: 20 }}>
            <thead>
              <tr><th>Year</th><th>Avg Package</th><th>Employment Rate</th></tr>
            </thead>
            <tbody>
              {compData.map((c, i) => (
                <tr key={i}>
                  <td>{c.year}</td>
                  <td>{formatPackage(c.average_package, c.package_currency)}</td>
                  <td>{c.employment_rate_percent ? `${c.employment_rate_percent}%` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* ── Sector-wise ──────────────────────────────────────────── */}
      {sectors.length > 0 && (
        <section className="content-section">
          <SectionTitle icon={<Briefcase size={20} />}>Sector-wise Placements</SectionTitle>
          <div ref={sectorView.ref} className="chart-card-full">
            <SectorBarChart data={sectors} animate={sectorView.inView} />
          </div>
          <table className="data-table" style={{ marginTop: 20 }}>
            <thead>
              <tr><th>Year</th><th>Sector</th><th>Companies</th><th>Share %</th></tr>
            </thead>
            <tbody>
              {sectors.map((s, i) => (
                <tr key={i}>
                  <td>{s.year}</td>
                  <td><strong>{s.sector}</strong></td>
                  <td className="text-muted-sm">{s.companies || '-'}</td>
                  <td>
                    <span className="pct-badge">{formatValue(s.percent)}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* ── Top Recruiters ───────────────────────────────────────── */}
      {recruiters.length > 0 && (
        <section className="content-section">
          <SectionTitle icon={<Building2 size={20} />}>Top Recruiters</SectionTitle>
          <div ref={recruiterView.ref} className="recruiter-logo-grid">
            {recruiters.map((r, i) => (
              <div
                className="recruiter-logo-card"
                key={i}
                style={{ '--i': i } as React.CSSProperties}
              >
                <div className="recruiter-avatar" style={{ background: logoColor(r) }}>
                  {r.charAt(0).toUpperCase()}
                </div>
                <span className="recruiter-name">{r}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Gender-wise Placement ────────────────────────────────── */}
      {genderPl.length > 0 && (
        <section className="content-section">
          <SectionTitle icon={<Users size={20} />}>Gender-wise Placement</SectionTitle>
          <div ref={genderView.ref} className="gender-pl-grid">
            {genderPl.map((g, i) => (
              <div className="gender-pl-card" key={i}>
                <div className="gender-pl-year">{g.year}</div>
                <GenderDonutChart
                  male={Number(g.male_percent) || 50}
                  female={Number(g.female_percent) || 50}
                  animate={genderView.inView}
                  compact
                />
                <div className="gender-pl-stats">
                  <ProgressBar
                    label={`Male (${formatValue(g.male_placed)} placed)`}
                    value={Number(g.male_percent) || 0}
                    color="#070642"
                    active={genderView.inView}
                  />
                  <ProgressBar
                    label={`Female (${formatValue(g.female_placed)} placed)`}
                    value={Number(g.female_percent) || 0}
                    color="#9a3197"
                    active={genderView.inView}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
