'use client';

import { GraduationCap, BookOpen, Home, DollarSign, Info, Award, BarChart2 } from 'lucide-react';
import dynamic from 'next/dynamic';
import { CollegeData, formatCurrency } from '../types';

const FeesBarChart = dynamic(() => import('../charts/FeesBarChart'), { ssr: false });

interface Props { college: CollegeData }

function SectionTitle({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <h2 className="section-title">
      <span className="section-icon">{icon}</span>
      {children}
    </h2>
  );
}

export default function FeesTab({ college }: Props) {
  const fd = college.fees_data;
  const fees = fd?.fees || college.fees;
  const feesByYear = fd?.fees_by_year || college.fees_by_year || [];
  const feesNote = fd?.fees_note || college.fees_note;
  const scholarshipsDetail = fd?.scholarships_detail || college.scholarships_detail || [];
  const scholarships = fd?.scholarships || college.scholarships || [];

  return (
    <div className="tab-content">

      {/* ── Main Fee Structure ──────────────────────────────────── */}
      <section className="content-section">
        <SectionTitle icon={<DollarSign size={20} />}>Fee Structure</SectionTitle>

        {(fees?.UG?.per_year || fees?.PG?.per_year || fees?.hostel_per_year) ? (
          <div className="fee-cards-row">
            {fees?.UG?.per_year && (
              <div className="fee-premium-card fee-ug">
                <div className="fee-premium-header">
                  <GraduationCap size={20} />
                  <span>Undergraduate (UG)</span>
                </div>
                <div className="fee-premium-amount">{fees.UG.per_year}</div>
                <div className="fee-premium-sublabel">Per Year · {fees.UG.currency || 'INR'}</div>
                {fees.UG.total_course && (
                  <div className="fee-premium-total">
                    <span>Total Course</span>
                    <strong>{fees.UG.total_course}</strong>
                  </div>
                )}
              </div>
            )}
            {fees?.PG?.per_year && (
              <div className="fee-premium-card fee-pg">
                <div className="fee-premium-header">
                  <BookOpen size={20} />
                  <span>Postgraduate (PG)</span>
                </div>
                <div className="fee-premium-amount">{fees.PG.per_year}</div>
                <div className="fee-premium-sublabel">Per Year · {fees.PG.currency || 'INR'}</div>
                {fees.PG.total_course && (
                  <div className="fee-premium-total">
                    <span>Total Course</span>
                    <strong>{fees.PG.total_course}</strong>
                  </div>
                )}
              </div>
            )}
            {fees?.hostel_per_year && (
              <div className="fee-premium-card fee-hostel">
                <div className="fee-premium-header">
                  <Home size={20} />
                  <span>Hostel</span>
                </div>
                <div className="fee-premium-amount">{fees.hostel_per_year}</div>
                <div className="fee-premium-sublabel">Per Year</div>
              </div>
            )}
          </div>
        ) : (fees?.ug_yearly_min || fees?.pg_yearly_min) ? (
          <div className="fees-grid">
            <div className="fee-card ug">
              <h3><GraduationCap size={16} style={{ marginRight: 6 }} />Undergraduate</h3>
              <div className="fee-range">
                <div className="fee-min">
                  <span className="fee-label">Minimum</span>
                  <span className="fee-amount">{formatCurrency(fees?.ug_yearly_min)}</span>
                </div>
                <span className="fee-arrow">→</span>
                <div className="fee-max">
                  <span className="fee-label">Maximum</span>
                  <span className="fee-amount">{formatCurrency(fees?.ug_yearly_max)}</span>
                </div>
              </div>
            </div>
            <div className="fee-card pg">
              <h3><BookOpen size={16} style={{ marginRight: 6 }} />Postgraduate</h3>
              <div className="fee-range">
                <div className="fee-min">
                  <span className="fee-label">Minimum</span>
                  <span className="fee-amount">{formatCurrency(fees?.pg_yearly_min)}</span>
                </div>
                <span className="fee-arrow">→</span>
                <div className="fee-max">
                  <span className="fee-label">Maximum</span>
                  <span className="fee-amount">{formatCurrency(fees?.pg_yearly_max)}</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <p className="no-data">No fee structure data available</p>
        )}
      </section>

      {/* ── Fees by Year ─────────────────────────────────────────── */}
      {feesByYear.length > 0 && (
        <section className="content-section">
          <SectionTitle icon={<BarChart2 size={20} />}>Fees Comparison</SectionTitle>
          <div className="chart-card-full" style={{ marginBottom: 24, padding: 20, background: 'rgba(255,255,255,0.03)', borderRadius: 16 }}>
            <FeesBarChart data={feesByYear} animate={true} />
          </div>
          <SectionTitle icon={<DollarSign size={20} />}>Detailed Fee Table</SectionTitle>
          <div className="table-container" style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Course / Year</th><th>Program</th><th>Per Year</th>
                  <th>Total Course</th><th>Hostel / Year</th><th>Currency</th>
                </tr>
              </thead>
              <tbody>
                {feesByYear.map((fy: any, i: number) => (
                  <tr key={i}>
                    <td>{fy.course || fy.year}</td>
                    <td><span className="program-type-badge">{fy.program_type || 'Degree'}</span></td>
                    <td>{fy.per_year_local || fy.year_1 || fy.per_year || '-'}</td>
                    <td>{fy.total_course_local || fy.total || fy.total_course || '-'}</td>
                    <td>{fy.hostel_per_year_local || '-'}</td>
                    <td>{fy.currency || 'INR'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── Fees Note ────────────────────────────────────────────── */}
      {feesNote && (
        <section className="content-section">
          <div className="info-callout">
            <Info size={15} style={{ marginRight: 8, flexShrink: 0 }} />
            <div>
              <strong>Note</strong><br />
              {feesNote}
            </div>
          </div>
        </section>
      )}

      {/* ── Scholarships ─────────────────────────────────────────── */}
      <section className="content-section">
        <SectionTitle icon={<Award size={20} />}>Scholarships</SectionTitle>

        {scholarshipsDetail.length > 0 ? (
          <div className="scholarship-cards">
            {scholarshipsDetail.map((s, i) => (
              <div className="scholarship-pro-card" key={i} style={{ '--i': i } as React.CSSProperties}>
                <div className="scholarship-pro-icon">
                  <Award size={20} />
                </div>
                <div className="scholarship-pro-body">
                  <div className="scholarship-pro-name">{s.name}</div>
                  {s.amount && (
                    <div className="scholarship-pro-amount">
                      <DollarSign size={12} />
                      {s.amount}
                    </div>
                  )}
                  {s.provider && (
                    <div className="scholarship-pro-provider">{s.provider}</div>
                  )}
                  {s.eligibility && (
                    <div className="scholarship-pro-eligibility">{s.eligibility}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : scholarships.length > 0 ? (
          <div className="scholarships-grid">
            {scholarships.map((s, i) => (
              <div className="scholarship-card" key={i}>
                <Award size={16} />
                <span className="scholarship-name">{s}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="no-data">No scholarships data available</p>
        )}
      </section>
    </div>
  );
}
