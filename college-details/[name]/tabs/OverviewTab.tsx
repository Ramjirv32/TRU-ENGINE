'use client';

import dynamic from 'next/dynamic';
import {
  GraduationCap, Users, Building2, Globe, Trophy, BookOpen,
  Microscope, Map, Phone, Mail, MapPin, ExternalLink, Calendar,
  TrendingUp, School,
} from 'lucide-react';
import { CollegeData, formatValue, isRealRank } from '../types';
import { useInView } from '../hooks';

const EnrollmentAreaChart = dynamic(() => import('../charts/EnrollmentAreaChart'), { ssr: false });
const GenderDonutChart = dynamic(() => import('../charts/GenderDonutChart'), { ssr: false });

interface Props {
  college: CollegeData;
}

function SectionTitle({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <h2 className="section-title">
      <span className="section-icon">{icon}</span>
      {children}
    </h2>
  );
}

function KVRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr>
      <td className="kv-label">{label}</td>
      <td className="kv-value">{value}</td>
    </tr>
  );
}

export default function OverviewTab({ college }: Props) {
  const enrollmentView = useInView();
  const genderView = useInView();

  const sd = college.student_statistics_detail;
  const fd = college.faculty_staff_detail;
  const sh = college.student_history;
  const id = college.infrastructure_data;
  const infra = id?.infrastructure || college.infrastructure || [];
  const hostel = id?.hostel_details || college.hostel_details;
  const library = id?.library_details || college.library_details;
  const transport = id?.transport_details || college.transport_details;

  const maleP = sh?.student_gender_ratio?.male_percent || college.student_gender_ratio?.male_percentage || 51;
  const femaleP = sh?.student_gender_ratio?.female_percent || college.student_gender_ratio?.female_percentage || 49;
  const hasGenderData = maleP > 0 || femaleP > 0;

  const rk = college.rankings;
  const rankRows = rk ? [
    { label: 'NIRF 2025', value: rk.nirf_2025 },
    { label: 'NIRF 2024', value: rk.nirf_2024 },
    { label: 'QS World', value: rk.qs_world },
    { label: 'QS Asia', value: rk.qs_asia },
    { label: 'THE World', value: rk.the_world },
    { label: 'National Rank', value: rk.national_rank },
    { label: 'State Rank', value: rk.state_rank },
  ].filter((r) => r.value !== null && r.value !== undefined && isRealRank(r.value)) : [];

  const enrollmentData = sh?.student_count_comparison_last_3_years ?? [];

  return (
    <div className="tab-content">

      {/* About */}
      <section className="content-section">
        <SectionTitle icon={<School size={20} />}>About {college.college_name}</SectionTitle>
        <div className="about-card">
          <p>{college.about || college.summary}</p>
        </div>
      </section>

      {/* Quick Facts */}
      {(college.established || college.institution_type || college.campus_area || college.website ||
        (college.accreditations?.length ?? 0) > 0 || (college.affiliations?.length ?? 0) > 0 || college.recognition) && (
        <section className="content-section">
          <SectionTitle icon={<Building2 size={20} />}>Quick Facts</SectionTitle>
          <table className="data-table">
            <thead><tr><th>Detail</th><th>Value</th></tr></thead>
            <tbody>
              {college.established && <KVRow label="Established" value={college.established} />}
              {college.institution_type && <KVRow label="Institution Type" value={college.institution_type} />}
              {college.campus_area && <KVRow label="Campus Area" value={college.campus_area} />}
              {college.recognition && <KVRow label="Recognition" value={college.recognition} />}
              {(college.accreditations?.length ?? 0) > 0 && (
                <KVRow label="Accreditations" value={college.accreditations!
                  .map((a) => `${a.body}${a.grade ? ` (${a.grade})` : ''}${a.year ? ` — ${a.year}` : ''}`)
                  .join(', ')} />
              )}
              {(college.affiliations?.length ?? 0) > 0 && (
                <KVRow label="Affiliations" value={college.affiliations!.join(', ')} />
              )}
              {college.website && (
                <KVRow label="Website" value={
                  <a href={college.website.startsWith('http') ? college.website : `https://${college.website}`}
                    target="_blank" rel="noopener noreferrer" className="table-link">
                    <ExternalLink size={13} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                    {college.website}
                  </a>
                } />
              )}
            </tbody>
          </table>
        </section>
      )}

      {/* Student Statistics */}
      <section className="content-section">
        <SectionTitle icon={<Users size={20} />}>Student Statistics</SectionTitle>
        {sd && (sd.total_enrollment > 0 || sd.ug_students > 0) ? (
          <div className="kpi-strip">
            {sd.total_enrollment ? (
              <div className="kpi-mini"><span className="kpi-mini-val">{sd.total_enrollment.toLocaleString()}</span><span className="kpi-mini-label">Total Enrolled</span></div>
            ) : null}
            {sd.ug_students ? (
              <div className="kpi-mini"><span className="kpi-mini-val">{sd.ug_students.toLocaleString()}</span><span className="kpi-mini-label">UG Students</span></div>
            ) : null}
            {sd.pg_students ? (
              <div className="kpi-mini"><span className="kpi-mini-val">{sd.pg_students.toLocaleString()}</span><span className="kpi-mini-label">PG Students</span></div>
            ) : null}
            {sd.phd_students ? (
              <div className="kpi-mini"><span className="kpi-mini-val">{sd.phd_students.toLocaleString()}</span><span className="kpi-mini-label">PhD Students</span></div>
            ) : null}
            {sd.annual_intake ? (
              <div className="kpi-mini"><span className="kpi-mini-val">{sd.annual_intake.toLocaleString()}</span><span className="kpi-mini-label">Annual Intake</span></div>
            ) : null}
            {sd.total_ug_courses ? (
              <div className="kpi-mini"><span className="kpi-mini-val">{sd.total_ug_courses}</span><span className="kpi-mini-label">UG Courses</span></div>
            ) : null}
            {sd.total_pg_courses ? (
              <div className="kpi-mini"><span className="kpi-mini-val">{sd.total_pg_courses}</span><span className="kpi-mini-label">PG Courses</span></div>
            ) : null}
            {sd.total_phd_courses ? (
              <div className="kpi-mini"><span className="kpi-mini-val">{sd.total_phd_courses}</span><span className="kpi-mini-label">PhD Courses</span></div>
            ) : null}
          </div>
        ) : (college.student_statistics?.length > 0 ? (
          <div className="stats-grid">
            {college.student_statistics.map((s, i) => (
              <div className="stat-box" key={i}>
                <span className="stat-box-value">{formatValue(s.value)}</span>
                <span className="stat-box-label">{s.category}</span>
              </div>
            ))}
          </div>
        ) : <p className="no-data">No student statistics available</p>)}
      </section>

      {/* Visual Analytics: enrollment area chart + gender donut */}
      {(enrollmentData.length > 0 || hasGenderData) && (
        <section className="content-section">
          <SectionTitle icon={<TrendingUp size={20} />}>Visual Analytics</SectionTitle>
          <div className="analytics-grid">
            {enrollmentData.length > 0 && (
              <div ref={enrollmentView.ref} className="chart-card">
                <div className="chart-card-header">
                  <TrendingUp size={16} />
                  <span>Enrollment Trends (3 Years)</span>
                </div>
                <EnrollmentAreaChart data={enrollmentData} animate={enrollmentView.inView} />
              </div>
            )}
            {hasGenderData && (
              <div ref={genderView.ref} className="chart-card">
                <div className="chart-card-header">
                  <Users size={16} />
                  <span>Gender Distribution</span>
                </div>
                <GenderDonutChart male={maleP} female={femaleP} animate={genderView.inView} />
                <div className="chart-legend">
                  <span className="legend-item"><span className="dot male" />{maleP}% Male</span>
                  <span className="legend-item"><span className="dot female" />{femaleP}% Female</span>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Rankings */}
      {rankRows.length > 0 && (
        <section className="content-section">
          <SectionTitle icon={<Trophy size={20} />}>Rankings</SectionTitle>
          <div className="rankings-cards">
            {rankRows.map((r) => (
              <div className="ranking-badge" key={r.label}>
                <span className="ranking-badge-value">{formatValue(r.value)}</span>
                <span className="ranking-badge-label">{r.label}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Faculty & Staff */}
      {fd && (fd.total_faculty > 0 || fd.student_faculty_ratio > 0) && (
        <section className="content-section">
          <SectionTitle icon={<GraduationCap size={20} />}>Faculty &amp; Staff</SectionTitle>
          <div className="kpi-strip">
            {fd.total_faculty ? <div className="kpi-mini"><span className="kpi-mini-val">{fd.total_faculty.toLocaleString()}</span><span className="kpi-mini-label">Total Faculty</span></div> : null}
            {fd.student_faculty_ratio ? <div className="kpi-mini"><span className="kpi-mini-val">{fd.student_faculty_ratio}:1</span><span className="kpi-mini-label">Student : Faculty</span></div> : null}
            {fd.phd_faculty_percent ? <div className="kpi-mini"><span className="kpi-mini-val">{fd.phd_faculty_percent}%</span><span className="kpi-mini-label">PhD Faculty</span></div> : null}
          </div>
        </section>
      )}

      {/* International Students */}
      {sh?.international_students?.total_count && (
        <section className="content-section">
          <SectionTitle icon={<Globe size={20} />}>International Students</SectionTitle>
          <div className="intl-card">
            <div className="intl-stat">
              <span className="intl-val">{sh.international_students.total_count.toLocaleString()}</span>
              <span className="intl-lbl">Total International Students</span>
            </div>
            {sh.international_students.international_percent > 0 && (
              <div className="intl-stat">
                <span className="intl-val">{sh.international_students.international_percent}%</span>
                <span className="intl-lbl">of Total Enrollment</span>
              </div>
            )}
            {(sh.international_students.countries_represented?.length ?? 0) > 0 && (
              <div className="intl-countries">
                <span className="intl-lbl" style={{ marginBottom: 8, display: 'block' }}>Top Countries</span>
                <div className="tag-row">
                  {sh.international_students.countries_represented.map((c) => (
                    <span className="tag-chip" key={c}><Globe size={11} />{c}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Infrastructure */}
      {infra.length > 0 && (
        <section className="content-section">
          <SectionTitle icon={<Building2 size={20} />}>Infrastructure</SectionTitle>
          <div className="infra-grid">
            {infra.map((item, i) => (
              <div className="infra-card" key={i}>
                <div className="infra-card-title"><Map size={14} />{item.facility}</div>
                <p className="infra-card-desc">{item.details}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Campus Facilities */}
      {(hostel?.available || library?.total_books || transport?.buses) && (
        <section className="content-section">
          <SectionTitle icon={<Building2 size={20} />}>Campus Facilities</SectionTitle>
          <div className="facilities-grid">
            {hostel?.available && (
              <div className="facility-card">
                <h4 className="facility-card-title"><Building2 size={15} />Hostel</h4>
                <table className="data-table compact">
                  <tbody>
                    {hostel.type && <KVRow label="Type" value={hostel.type} />}
                    {hostel.boys_capacity && <KVRow label="Boys Capacity" value={formatValue(hostel.boys_capacity)} />}
                    {hostel.girls_capacity && <KVRow label="Girls Capacity" value={formatValue(hostel.girls_capacity)} />}
                    {hostel.total_capacity && <KVRow label="Total Capacity" value={formatValue(hostel.total_capacity)} />}
                  </tbody>
                </table>
              </div>
            )}
            {library?.total_books && (
              <div className="facility-card">
                <h4 className="facility-card-title"><BookOpen size={15} />Library</h4>
                <table className="data-table compact">
                  <tbody>
                    {library.total_books && <KVRow label="Total Books" value={library.total_books} />}
                    {library.journals && <KVRow label="Journals" value={library.journals} />}
                    {library.e_resources && <KVRow label="E-Resources" value={library.e_resources} />}
                    {library.area_sqft && <KVRow label="Area" value={`${library.area_sqft} sq ft`} />}
                  </tbody>
                </table>
              </div>
            )}
            {transport?.buses && (
              <div className="facility-card">
                <h4 className="facility-card-title"><Map size={15} />Transport</h4>
                <table className="data-table compact">
                  <tbody>
                    {transport.buses && <KVRow label="Buses" value={transport.buses} />}
                    {transport.routes && <KVRow label="Routes" value={transport.routes} />}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Contact Info */}
      {college.contact_info && (college.contact_info.phone || college.contact_info.email || college.contact_info.address) && (
        <section className="content-section">
          <SectionTitle icon={<Phone size={20} />}>Contact Information</SectionTitle>
          <div className="contact-card">
            {college.contact_info.phone && (
              <div className="contact-row"><Phone size={16} /><span>{college.contact_info.phone}</span></div>
            )}
            {college.contact_info.email && (
              <div className="contact-row"><Mail size={16} /><a href={`mailto:${college.contact_info.email}`}>{college.contact_info.email}</a></div>
            )}
            {college.contact_info.address && (
              <div className="contact-row"><MapPin size={16} /><span>{college.contact_info.address}</span></div>
            )}
          </div>
        </section>
      )}

      {/* Legacy additional_details fallback */}
      {(!college.rankings || !Object.values(college.rankings).some((v) => v)) && (college.additional_details?.length > 0) && (
        <section className="content-section">
          <SectionTitle icon={<Microscope size={20} />}>Additional Details</SectionTitle>
          <div className="details-grid">
            {college.additional_details.map((d, i) => (
              <div className="detail-card" key={i}>
                <span className="detail-label">{d.category}</span>
                <span className="detail-value">{formatValue(d.value)}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
