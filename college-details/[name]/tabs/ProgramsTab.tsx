'use client';

import { GraduationCap, BookOpen, Microscope } from 'lucide-react';
import { CollegeData } from '../types';

interface Props { college: CollegeData }

function SectionTitle({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <h2 className="section-title">
      <span className="section-icon">{icon}</span>
      {children}
    </h2>
  );
}

function ProgramGrid({ programs, variant }: { programs: string[]; variant: 'ug' | 'pg' | 'phd' }) {
  const badge: Record<string, string> = { ug: 'UG', pg: 'PG', phd: 'PhD' };
  return (
    <div className="programs-grid">
      {programs.map((p, i) => (
        <div
          className={`program-card program-card--${variant}`}
          key={i}
          style={{ '--i': i } as React.CSSProperties}
        >
          <span className={`program-badge program-badge--${variant}`}>{badge[variant]}</span>
          <span className="program-name">{p}</span>
        </div>
      ))}
    </div>
  );
}

export default function ProgramsTab({ college }: Props) {
  const ugProgs = college.programs_data?.ug_programs || college.ug_programs || [];
  const pgProgs = college.programs_data?.pg_programs || college.pg_programs || [];
  const phdProgs = college.programs_data?.phd_programs || college.phd_programs || [];

  return (
    <div className="tab-content">

      <section className="content-section">
        <SectionTitle icon={<GraduationCap size={20} />}>
          Undergraduate Programs
          {ugProgs.length > 0 && (
            <span className="count-chip">{ugProgs.length}</span>
          )}
        </SectionTitle>
        {ugProgs.length > 0
          ? <ProgramGrid programs={ugProgs} variant="ug" />
          : <p className="no-data">No UG programs data available</p>}
      </section>

      <section className="content-section">
        <SectionTitle icon={<BookOpen size={20} />}>
          Postgraduate Programs
          {pgProgs.length > 0 && (
            <span className="count-chip">{pgProgs.length}</span>
          )}
        </SectionTitle>
        {pgProgs.length > 0
          ? <ProgramGrid programs={pgProgs} variant="pg" />
          : <p className="no-data">No PG programs data available</p>}
      </section>

      <section className="content-section">
        <SectionTitle icon={<Microscope size={20} />}>
          PhD Programs
          {phdProgs.length > 0 && (
            <span className="count-chip">{phdProgs.length}</span>
          )}
        </SectionTitle>
        {phdProgs.length > 0
          ? <ProgramGrid programs={phdProgs} variant="phd" />
          : <p className="no-data">No PhD programs data available</p>}
      </section>
    </div>
  );
}
