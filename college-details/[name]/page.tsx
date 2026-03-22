'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
    Chart,
    ArcElement,
    DoughnutController,
    BarController,
    BarElement,
    LineController,
    LineElement,
    PointElement,
    CategoryScale,
    LinearScale,
    Tooltip,
    Legend,
    Filler,
} from 'chart.js';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import './styles.css';
import { API_URL, WS_URL } from '@/lib/config';
import { useWebSocket } from '@/hooks/useWebSocket';

// Dynamic imports for Tabs to keep initial bundle size small
const OverviewTab = dynamic(() => import('./tabs/OverviewTab'), { ssr: false });
const ProgramsTab = dynamic(() => import('./tabs/ProgramsTab'), { ssr: false });
const DepartmentsTab = dynamic(() => import('./tabs/DepartmentsTab'), { ssr: false });
const PlacementsTab = dynamic(() => import('./tabs/PlacementsTab'), { ssr: false });
const FeesTab = dynamic(() => import('./tabs/FeesTab'), { ssr: false });


interface FeeGroup {
    per_year: string;
    total_course: string;
    currency: string;
}

interface FeesInfo {
    UG: FeeGroup;
    PG: FeeGroup;
    hostel_per_year: string;
    ug_yearly_min?: number;
    ug_yearly_max?: number;
    pg_yearly_min?: number;
    pg_yearly_max?: number;
    phd_yearly_min?: number;
    phd_yearly_max?: number;
}

interface FeesYearInfo {
    year: string;
    program_type: string;
    per_year_local: string;
    total_course_local: string;
    hostel_per_year_local: string;
    currency: string;
}

interface GenderRatio {
    male_percentage: number;
    female_percentage: number;
}

interface GenderRatioDetail {
    total_male: number;
    total_female: number;
    male_percent: number;
    female_percent: number;
}

interface StatisticItem {
    category: string;
    value: any;
}

interface CollegeRankings {
    nirf_2025?: any;
    nirf_2024?: any;
    qs_world?: any;
    qs_asia?: any;
    the_world?: any;
    national_rank?: any;
    state_rank?: any;
}

interface StudentStatsDetail {
    total_enrollment: number;
    ug_students: number;
    pg_students: number;
    phd_students: number;
    annual_intake: number;
    male_percent: number;
    female_percent: number;
    total_ug_courses: number;
    total_pg_courses: number;
    total_phd_courses: number;
}

interface FacultyStaffDetail {
    total_faculty: number;
    student_faculty_ratio: number;
    phd_faculty_percent: number;
}

interface PlacementInfo {
    year: number;
    highest_package: number;
    average_package: number;
    median_package: number;
    package_currency: string;
    placement_rate_percent: number;
    total_students_placed: number;
    total_companies_visited: number;
    graduate_outcomes_note: string;
}

interface PlacementComp {
    year: number;
    average_package: number;
    employment_rate_percent: number;
    package_currency: string;
}

interface GenderPlacement {
    year: number;
    male_placed: any;
    female_placed: any;
    male_percent: any;
    female_percent: any;
}

interface SectorPlacement {
    year: number;
    sector: string;
    companies: string;
    percent: any;
}

interface ScholarshipItem {
    name: string;
    amount: string;
    eligibility: string;
    provider: string;
}

interface InfraItem {
    facility: string;
    details: string;
}

interface HostelDetails {
    available: boolean;
    boys_capacity: any;
    girls_capacity: any;
    total_capacity: any;
    type: string;
}

interface LibraryDetails {
    total_books: string;
    journals: string;
    e_resources: string;
    area_sqft: string;
}

interface TransportDetails {
    buses: string;
    routes: string;
}

interface StudentCountEntry {
    year: number;
    total_enrolled: number;
    ug: number;
    pg: number;
    phd: number;
}

interface StudentHistory {
    student_count_comparison_last_3_years: StudentCountEntry[];
    student_gender_ratio: GenderRatioDetail;
    international_students: { total_count: number; countries_represented: string[]; international_percent: number };
    notable_faculty: { name: string; designation: string; specialization: string }[];
    faculty_achievements: string;
}

interface Accreditation {
    body: string;
    grade: any;
    year: any;
}

interface ContactInfo {
    phone: string;
    email: string;
    address: string;
}

interface CollegeData {
    college_name: string;
    short_name?: string;
    established?: number;
    institution_type?: string;
    country: string;
    about: string;
    location: string;
    website?: string;
    summary: string;
    ug_programs: string[];
    pg_programs: string[];
    phd_programs: string[];

    rankings?: CollegeRankings;
    student_statistics_detail?: StudentStatsDetail;
    faculty_staff_detail?: FacultyStaffDetail;
    placements?: PlacementInfo;
    placement_comparison_last_3_years?: PlacementComp[];
    gender_based_placement_last_3_years?: GenderPlacement[];
    sector_wise_placement_last_3_years?: SectorPlacement[];
    top_recruiters?: string[];
    placement_highlights?: string;

    fees: FeesInfo;
    fees_by_year?: FeesYearInfo[];
    fees_note?: string;
    scholarships_detail?: ScholarshipItem[];

    infrastructure?: InfraItem[];
    hostel_details?: HostelDetails;
    library_details?: LibraryDetails;
    transport_details?: TransportDetails;

    student_history?: StudentHistory;
    accreditations?: Accreditation[];
    affiliations?: string[];
    recognition?: string;
    campus_area?: string;
    contact_info?: ContactInfo;

    // Legacy/compat
    scholarships?: string[];
    student_gender_ratio: GenderRatio;
    faculty_staff: number;
    international_students: number;
    global_ranking: string | { qs_world?: any; the_world?: any; us_news_global?: any; arwu?: any; webometrics?: any };
    departments: string[];
    student_statistics: StatisticItem[];
    additional_details: StatisticItem[];
    sources: string[];
    approval_status: string;
}

export default function CollegeDetailsPage() {
    const params = useParams();
    const router = useRouter();
    const collegeName = decodeURIComponent(params.name as string);

    const [collegeData, setCollegeData] = useState<CollegeData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedDepartment, setSelectedDepartment] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'overview' | 'programs' | 'departments' | 'placements' | 'fees'>('overview');
    const [scrapingStatus, setScrapingStatus] = useState<string | null>(null);
    const [lastUpdatedSection, setLastUpdatedSection] = useState<string | null>(null);

    const genderChartRef = useRef<Chart | null>(null);
    const programsChartRef = useRef<Chart | null>(null);
    const placementChartRef = useRef<Chart | null>(null);

    // WebSocket for real-time updates
    const wsUrl = collegeName ? `${WS_URL}/ws/college-details/${encodeURIComponent(collegeName)}` : '';

    useWebSocket(wsUrl, {
        onMessage: (message) => {
            if (message.type === 'initial_data' && !collegeData) {
                setCollegeData(message.data);
                if (message.data.departments?.length > 0) {
                    setSelectedDepartment(message.data.departments[0]);
                }
            } else if (message.type === 'scraping_update') {
                console.log('🚀 Live Scraping Update:', message);
                setScrapingStatus(message.update_type);

                if (message.update_type === 'section_complete' && message.data) {
                    const section = message.data.section;
                    setLastUpdatedSection(section);

                    // Merge new section data into current state
                    setCollegeData(prev => {
                        if (!prev) return null;
                        const newData = { ...prev };

                        // Targeted merge based on section
                        const sectionData = message.data.data;
                        if (section === 'programs') {
                            newData.ug_programs = sectionData.ug_programs || prev.ug_programs;
                            newData.pg_programs = sectionData.pg_programs || prev.pg_programs;
                            newData.phd_programs = sectionData.phd_programs || prev.phd_programs;
                            newData.departments = sectionData.departments || prev.departments;
                        } else if (section === 'placements') {
                            if (sectionData.placements) newData.placements = sectionData.placements;
                            if (sectionData.placement_comparison_last_3_years) newData.placement_comparison_last_3_years = sectionData.placement_comparison_last_3_years;
                            if (sectionData.top_recruiters) newData.top_recruiters = sectionData.top_recruiters;
                            if (sectionData.sector_wise_placement_last_3_years) newData.sector_wise_placement_last_3_years = sectionData.sector_wise_placement_last_3_years;
                            if (sectionData.gender_based_placement_last_3_years) newData.gender_based_placement_last_3_years = sectionData.gender_based_placement_last_3_years;
                            if (sectionData.placement_highlights) newData.placement_highlights = sectionData.placement_highlights;
                            // Legacy compat
                            if (message.data.student_statistics) newData.student_statistics = message.data.student_statistics;
                        } else if (section === 'fees') {
                            newData.fees = sectionData.fees || prev.fees;
                            newData.fees_by_year = sectionData.fees_by_year || prev.fees_by_year;
                            newData.fees_note = sectionData.fees_note || prev.fees_note;
                            newData.scholarships_detail = sectionData.scholarships_detail || sectionData.scholarships || prev.scholarships_detail;
                        } else if (section === 'infrastructure') {
                            newData.infrastructure = sectionData.infrastructure || prev.infrastructure;
                            newData.hostel_details = sectionData.hostel_details || prev.hostel_details;
                            newData.library_details = sectionData.library_details || prev.library_details;
                            newData.transport_details = sectionData.transport_details || prev.transport_details;
                        }

                        return newData;
                    });

                    // Clear highlight after 3 seconds
                    setTimeout(() => {
                        setLastUpdatedSection(null);
                        setScrapingStatus(null);
                    }, 3000);
                } else if (message.update_type === 'phase1_complete') {
                    // Refetch or merge phase 1 data
                    fetchCollegeDetails();
                }
            }
        }
    });

    const fetchCollegeDetails = async () => {
        try {
            setLoading(true);
            const response = await fetch(
                `${API_URL}/api/college-statistics?college_name=${encodeURIComponent(collegeName)}`
            );
            const data: any = await response.json();

            if (data.error) {
                setError(data.error);
            } else {
                // Flatten nested data for easier access in components
                const flattenedData = { ...data };
                if (data.programs_data) {
                    flattenedData.ug_programs = data.programs_data.ug_programs || data.ug_programs;
                    flattenedData.pg_programs = data.programs_data.pg_programs || data.pg_programs;
                    flattenedData.phd_programs = data.programs_data.phd_programs || data.phd_programs;
                    flattenedData.departments = data.programs_data.departments || data.departments;
                }
                if (data.placements_data) {
                    flattenedData.placements = data.placements_data.placements || data.placements;
                    flattenedData.placement_comparison_last_3_years = data.placements_data.placement_comparison_last_3_years || data.placement_comparison_last_3_years;
                    flattenedData.top_recruiters = data.placements_data.top_recruiters || data.top_recruiters;
                    flattenedData.placement_highlights = data.placements_data.placement_highlights || data.placement_highlights;
                }
                if (data.fees_data) {
                    flattenedData.fees = data.fees_data.fees || data.fees;
                    flattenedData.fees_by_year = data.fees_data.fees_by_year || data.fees_by_year;
                    flattenedData.fees_note = data.fees_data.fees_note || data.fees_note;
                    flattenedData.scholarships_detail = data.fees_data.scholarships_detail || data.scholarships_detail;
                }
                if (data.infrastructure_data) {
                    flattenedData.infrastructure = data.infrastructure_data.infrastructure || data.infrastructure;
                    flattenedData.hostel_details = data.infrastructure_data.hostel_details || data.hostel_details;
                    flattenedData.library_details = data.infrastructure_data.library_details || data.library_details;
                    flattenedData.transport_details = data.infrastructure_data.transport_details || data.transport_details;
                }

                setCollegeData(flattenedData);

                if (flattenedData.departments && flattenedData.departments.length > 0) {
                    setSelectedDepartment(flattenedData.departments[0]);
                }
            }
        } catch (err) {
            setError('Failed to fetch college data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCollegeDetails();
    }, [collegeName]);

    useEffect(() => {
        if (collegeData && activeTab === 'overview') {
            setTimeout(() => {
                createGenderChart();
                createProgramsChart();
            }, 300);
        }
        if (collegeData && activeTab === 'placements') {
            setTimeout(() => {
                createPlacementChart();
            }, 300);
        }

        return () => {
            if (genderChartRef.current) genderChartRef.current.destroy();
            if (programsChartRef.current) programsChartRef.current.destroy();
            if (placementChartRef.current) placementChartRef.current.destroy();
        };
    }, [collegeData, activeTab]);

    // --- Helper Utilities ---
    const formatValue = (val: any): string => {
        if (val === null || val === undefined || val === '' || val === 0) return '-';
        if (typeof val === 'object') return JSON.stringify(val);
        return String(val);
    };

    const formatPackage = (amount: number, currency: string = 'INR'): string => {
        if (!amount) return '-';
        const sym = currency === 'USD' ? '$' : '₹';
        if (currency === 'USD') return `${sym}${amount.toLocaleString()}`;
        if (amount >= 100000) return `${sym}${(amount / 100000).toFixed(2)} LPA`;
        return `${sym}${amount.toLocaleString()}`;
    };

    const formatCurrency = (amount: any, currency: string = '₹'): string => {
        if (!amount) return 'N/A';
        if (typeof amount === 'string') return amount; // Already formatted string from FeeGroup
        if (typeof amount === 'number') {
            if (amount >= 100000) return `${currency}${(amount / 100000).toFixed(1)}L`;
            return `${currency}${amount.toLocaleString()}`;
        }
        return String(amount);
    };

    // Legacy helpers (fallback)
    const getStat = (keyword: string): any => {
        const stat = collegeData?.student_statistics?.find((s) =>
            s.category.toLowerCase().includes(keyword.toLowerCase())
        );
        const val = stat?.value;
        if (val === null || val === undefined) return 0;
        if (typeof val === 'object') return JSON.stringify(val);
        return val;
    };

    const getDetail = (keyword: string): any => {
        const detail = collegeData?.additional_details?.find((d) =>
            d.category.toLowerCase().includes(keyword.toLowerCase())
        );
        const val = detail?.value;
        if (val === null || val === undefined) return '-';
        if (typeof val === 'object') return JSON.stringify(val);
        return val;
    };

    const createGenderChart = () => {
        const canvas = document.getElementById('genderChart') as HTMLCanvasElement;
        if (!canvas || !collegeData) return;
        if (genderChartRef.current) genderChartRef.current.destroy();

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Prefer structured student_history gender ratio, fallback to legacy
        const sh = collegeData.student_history?.student_gender_ratio;
        const legacy = collegeData.student_gender_ratio;
        const maleP = sh?.male_percent || legacy?.male_percentage || 50;
        const femaleP = sh?.female_percent || legacy?.female_percentage || 50;

        genderChartRef.current = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Male', 'Female'],
                datasets: [
                    {
                        data: [maleP, femaleP],
                        backgroundColor: ['#070642', '#9a3197'],
                        borderWidth: 0,
                        hoverOffset: 15,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: true },
                },
            },
        });
    };

    const createProgramsChart = () => {
        const canvas = document.getElementById('programsChart') as HTMLCanvasElement;
        if (!canvas || !collegeData) return;
        if (programsChartRef.current) programsChartRef.current.destroy();

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        programsChartRef.current = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['UG Programs', 'PG Programs', 'PhD Programs'],
                datasets: [
                    {
                        label: 'Number of Programs',
                        data: [
                            collegeData.ug_programs?.length || 0,
                            collegeData.pg_programs?.length || 0,
                            collegeData.phd_programs?.length || 0,
                        ],
                        backgroundColor: ['#070642', '#9a3197', '#e084cd'],
                        borderRadius: 8,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
                    x: { grid: { display: false } },
                },
            },
        });
    };

    const createPlacementChart = () => {
        const canvas = document.getElementById('placementChart') as HTMLCanvasElement;
        if (!canvas || !collegeData) return;
        if (placementChartRef.current) placementChartRef.current.destroy();

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const compData = collegeData.placement_comparison_last_3_years || [];
        const labels = compData.map(c => String(c.year));
        const avgPkgs = compData.map(c => c.average_package || 0);
        const empRates = compData.map(c => c.employment_rate_percent || 0);

        placementChartRef.current = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels.length > 0 ? labels : ['No Data'],
                datasets: [
                    {
                        label: 'Avg Package (LPA)',
                        data: avgPkgs.length > 0 ? avgPkgs.map(v => v >= 100000 ? +(v / 100000).toFixed(2) : v) : [0],
                        backgroundColor: '#070642',
                        borderRadius: 8,
                        yAxisID: 'y',
                    },
                    {
                        label: 'Employment Rate %',
                        data: empRates.length > 0 ? empRates : [0],
                        backgroundColor: '#9a3197',
                        borderRadius: 8,
                        yAxisID: 'y1',
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, position: 'top' },
                },
                scales: {
                    y: { beginAtZero: true, position: 'left', grid: { color: 'rgba(0,0,0,0.05)' }, title: { display: true, text: 'Package' } },
                    y1: { beginAtZero: true, position: 'right', max: 100, grid: { drawOnChartArea: false }, title: { display: true, text: '% Rate' } },
                    x: { grid: { display: false } },
                },
            },
        });
    };

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner"></div>
                <p>Loading College Data...</p>
            </div>
        );
    }

    if (error || !collegeData) {
        return (
            <div className="error-container">
                <h2>❌ Error Loading Data</h2>
                <p>{error || 'College not found'}</p>
                <Link href="/" className="back-btn">
                    ← Back to Home
                </Link>
            </div>
        );
    }

    return (
        <div className="college-details-page">
            { }
            <section className="hero-section">
                <div className="hero-content">
                    <Link href="/" className="back-link">
                        ← Back to Home
                    </Link>
                    <h1 className="college-name">
                        {collegeData.college_name}
                        {collegeData.approval_status === 'fetching' && (
                            <span className="live-badge">
                                <span className="pulse"></span> LIVE SYNCING
                            </span>
                        )}
                    </h1>
                    <p className="college-location">
                        📍 {collegeData.location}, {collegeData.country}
                    </p>
                    <p className="college-summary">{collegeData.summary || collegeData.about}</p>

                    {scrapingStatus && (
                        <div className="scraping-progress">
                            <div className="progress-info">
                                <span className="progress-text">
                                    {scrapingStatus === 'fetching' ? 'Initializing Scrapers...' :
                                        scrapingStatus === 'phase1_complete' ? 'Core Data Extracted' :
                                            scrapingStatus === 'section_complete' ? `Updating ${lastUpdatedSection ?? 'data'}...` :
                                                'Scraping detailed info...'}
                                </span>
                                <div className="mini-spinner"></div>
                            </div>
                        </div>
                    )}

                    { }
                    <div className="quick-stats">
                        <div className="stat-card">
                            <span className="stat-icon">👨‍🎓</span>
                            <span className="stat-value">{collegeData.student_statistics_detail?.total_enrollment ? collegeData.student_statistics_detail.total_enrollment.toLocaleString() : (getStat('total students') || '-')}</span>
                            <span className="stat-label">Total Students</span>
                        </div>
                        <div className="stat-card">
                            <span className="stat-icon">🏛️</span>
                            <span className="stat-value">{collegeData.departments?.length || 0}</span>
                            <span className="stat-label">Departments</span>
                        </div>
                        <div className="stat-card">
                            <span className="stat-icon">🎓</span>
                            <span className="stat-value">{(collegeData.ug_programs?.length || 0) + (collegeData.pg_programs?.length || 0) + (collegeData.phd_programs?.length || 0)}</span>
                            <span className="stat-label">Total Courses</span>
                        </div>
                        <div className="stat-card">
                            <span className="stat-icon">👨‍🏫</span>
                            <span className="stat-value">{collegeData.faculty_staff_detail?.total_faculty || collegeData.faculty_staff || '-'}</span>
                            <span className="stat-label">Faculty</span>
                        </div>
                        <div className="stat-card">
                            <span className="stat-icon">🌍</span>
                            <span className="stat-value">{collegeData.student_history?.international_students?.total_count || collegeData.international_students || '-'}</span>
                            <span className="stat-label">International</span>
                        </div>
                        <div className="stat-card">
                            <span className="stat-icon">🏆</span>
                            {(() => {
                                const isRealRank = (v: any) => v !== null && v !== undefined && v !== '' && v !== 0 && v !== 'N/A' && v !== 'N/a' && v !== 'n/a';
                                const rk = collegeData.rankings;
                                const candidates: { label: string; value: any }[] = rk ? [
                                    { label: 'NIRF 2025', value: rk.nirf_2025 },
                                    { label: 'NIRF 2024', value: rk.nirf_2024 },
                                    { label: 'National Rank', value: rk.national_rank },
                                    { label: 'State Rank', value: rk.state_rank },
                                    { label: 'QS World', value: rk.qs_world },
                                    { label: 'THE World', value: rk.the_world },
                                ] : [];
                                const found = candidates.find(c => isRealRank(c.value));
                                if (found) return (
                                    <>
                                        <span className="stat-value">{formatValue(found.value)}</span>
                                        <span className="stat-label">{found.label}</span>
                                    </>
                                );
                                // Legacy fallback
                                const r = collegeData.global_ranking;
                                const legacyVal = r && typeof r === 'object'
                                    ? [r.qs_world, r.the_world, r.us_news_global, r.arwu, r.webometrics].find(isRealRank)
                                    : (typeof r === 'string' && isRealRank(r) ? r : null);
                                return (
                                    <>
                                        <span className="stat-value">{legacyVal ? String(legacyVal) : '-'}</span>
                                        <span className="stat-label">Ranking</span>
                                    </>
                                );
                            })()}
                        </div>
                    </div>
                </div>
            </section>

            { }
            <div className="tabs-container">
                <div className="tabs">
                    {['overview', 'programs', 'departments', 'placements', 'fees'].map((tab) => (
                        <button
                            key={tab}
                            className={`tab ${activeTab === tab ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab as any)}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            { }
            <main className="main-content">
                {activeTab === 'overview' && <OverviewTab college={collegeData} />}
                {activeTab === 'programs' && <ProgramsTab college={collegeData} />}
                {activeTab === 'departments' && <DepartmentsTab college={collegeData} selected={selectedDepartment} onSelect={setSelectedDepartment} />}
                {activeTab === 'placements' && <PlacementsTab college={collegeData} />}
                {activeTab === 'fees' && <FeesTab college={collegeData} />}

                {/* Sources Section (always show at the bottom of the active tab) */}
                {collegeData.sources && collegeData.sources.length > 0 && (
                    <section className="content-section sources-section">
                        <h2 className="section-title">📖 Data Sources</h2>
                        <div className="sources-list">
                            {collegeData.sources.map((source, idx) => (
                                <a
                                    key={idx}
                                    href={source}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="source-link"
                                >
                                    {source}
                                </a>
                            ))}
                        </div>
                    </section>
                )}
            </main>

            { }
            <footer className="page-footer">
                <button onClick={() => router.push('/')} className="back-home-btn">
                    ← Return to Home
                </button>
            </footer>
        </div>
    );
}
