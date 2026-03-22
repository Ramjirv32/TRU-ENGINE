'use client';

import { useState } from 'react';
import { Building2, ChevronRight } from 'lucide-react';
import { CollegeData } from '../types';

interface Props {
  college: CollegeData;
  selected: string | null;
  onSelect: (dept: string) => void;
}

function SectionTitle({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <h2 className="section-title">
      <span className="section-icon">{icon}</span>
      {children}
    </h2>
  );
}

export default function DepartmentsTab({ college, selected, onSelect }: Props) {
  const depts = college.programs_data?.departments || college.departments || [];

  return (
    <div className="tab-content">

      <section className="content-section">
        <SectionTitle icon={<Building2 size={20} />}>
          Departments
          {depts.length > 0 && <span className="count-chip">{depts.length}</span>}
        </SectionTitle>

        {depts.length > 0 ? (
          <div className="departments-split">
            {/* Left: scrollable list */}
            <div className="departments-list">
              <div className="list-header">
                <Building2 size={14} />
                Select Department
              </div>
              <div className="list-items">
                {depts.map((dept, i) => (
                  <button
                    key={i}
                    className={`dept-item ${selected === dept ? 'active' : ''}`}
                    onClick={() => onSelect(dept)}
                  >
                    <span className="dept-item-text">{dept}</span>
                    <ChevronRight size={14} className="dept-item-arrow" />
                  </button>
                ))}
              </div>
            </div>

            {/* Right: detail pane */}
            <div className="department-details">
              {selected ? (
                <>
                  <h3 className="dept-name">{selected}</h3>
                  <p className="dept-description">
                    {college.college_name} — {selected}
                  </p>
                  {/* Show related programs */}
                  <div className="related-programs">
                    <h4>Related Programs</h4>
                    <div className="related-list">
                      {[
                        ...(college.ug_programs ?? []),
                        ...(college.pg_programs ?? []),
                        ...(college.phd_programs ?? []),
                      ]
                        .filter((p) => p.toLowerCase().includes(selected.split(' ')[0].toLowerCase()))
                        .slice(0, 8)
                        .map((p, i) => (
                          <span className="related-tag" key={i}>{p}</span>
                        ))}
                    </div>
                    {[
                      ...(college.ug_programs ?? []),
                      ...(college.pg_programs ?? []),
                      ...(college.phd_programs ?? []),
                    ].filter((p) => p.toLowerCase().includes(selected.split(' ')[0].toLowerCase())).length === 0 && (
                      <p className="no-related">No directly matching programs found.</p>
                    )}
                  </div>
                </>
              ) : (
                <div className="dept-empty-state">
                  <Building2 size={40} strokeWidth={1} style={{ opacity: 0.2, marginBottom: 12 }} />
                  <p className="select-prompt">Select a department from the list to view details</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <p className="no-data">No departments data available</p>
        )}
      </section>

      {/* Tag cloud */}
      {depts.length > 0 && (
        <section className="content-section">
          <SectionTitle icon={<Building2 size={20} />}>All Departments</SectionTitle>
          <div className="departments-grid">
            {depts.map((dept, i) => (
              <button
                key={i}
                className="dept-tag"
                onClick={() => onSelect(dept)}
                style={{ '--i': i } as React.CSSProperties}
              >
                {dept}
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
