// ─── Shared types for college-details page ────────────────────────────────

export interface FeeGroup {
  per_year: string;
  total_course: string;
  currency: string;
}

export interface FeesInfo {
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

export interface FeesYearInfo {
  year: string;
  program_type: string;
  per_year_local: string;
  total_course_local: string;
  hostel_per_year_local: string;
  currency: string;
}

export interface GenderRatio {
  male_percentage: number;
  female_percentage: number;
}

export interface GenderRatioDetail {
  total_male: number;
  total_female: number;
  male_percent: number;
  female_percent: number;
}

export interface StatisticItem {
  category: string;
  value: any;
}

export interface CollegeRankings {
  nirf_2025?: any;
  nirf_2024?: any;
  qs_world?: any;
  qs_asia?: any;
  the_world?: any;
  national_rank?: any;
  state_rank?: any;
}

export interface StudentStatsDetail {
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

export interface FacultyStaffDetail {
  total_faculty: number;
  student_faculty_ratio: number;
  phd_faculty_percent: number;
}

export interface PlacementInfo {
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

export interface PlacementComp {
  year: number;
  average_package: number;
  employment_rate_percent: number;
  package_currency: string;
}

export interface GenderPlacement {
  year: number;
  male_placed: any;
  female_placed: any;
  male_percent: any;
  female_percent: any;
}

export interface SectorPlacement {
  year: number;
  sector: string;
  companies: string;
  percent: any;
}

export interface ScholarshipItem {
  name: string;
  amount: string;
  eligibility: string;
  provider: string;
}

export interface InfraItem {
  facility: string;
  details: string;
}

export interface HostelDetails {
  available: boolean;
  boys_capacity: any;
  girls_capacity: any;
  total_capacity: any;
  type: string;
}

export interface LibraryDetails {
  total_books: string;
  journals: string;
  e_resources: string;
  area_sqft: string;
}

export interface TransportDetails {
  buses: string;
  routes: string;
}

export interface StudentCountEntry {
  year: number;
  total_enrolled: number;
  ug: number;
  pg: number;
  phd: number;
}

export interface StudentHistory {
  student_count_comparison_last_3_years: StudentCountEntry[];
  student_gender_ratio: GenderRatioDetail;
  international_students: {
    total_count: number;
    countries_represented: string[];
    international_percent: number;
  };
  notable_faculty: { name: string; designation: string; specialization: string }[] | null;
  faculty_achievements: string;
}

export interface Accreditation {
  body: string;
  grade: any;
  year: any;
}

export interface ContactInfo {
  phone: string;
  email: string;
  address: string;
}

export interface CollegeData {
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
  programs_data?: {
    ug_programs: string[];
    pg_programs: string[];
    phd_programs: string[];
    departments: string[];
    extracted_content?: string;
    raw_output?: string;
    error?: string;
  };
  placements_data?: {
    data_year: string;
    sources: string[];
    placements: PlacementInfo;
    placement_comparison_last_3_years: PlacementComp[];
    top_recruiters: string[];
    placement_highlights: string;
    gender_based_placement_last_3_years?: GenderPlacement[];
    sector_wise_placement_last_3_years?: SectorPlacement[];
  };
  fees_data?: {
    fees: FeesInfo;
    fees_by_year: FeesYearInfo[];
    fees_note: string;
    scholarships_detail: ScholarshipItem[];
    scholarships?: string[];
    sources?: string[];
    extracted_content?: string;
    raw_output?: string;
    error?: string;
  };
  infrastructure_data?: {
    infrastructure: InfraItem[];
    hostel_details: HostelDetails;
    library_details: LibraryDetails;
    transport_details: TransportDetails;
    extracted_content?: string;
    raw_output?: string;
    error?: string;
  };
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

// ─── Helpers ──────────────────────────────────────────────────────────────

export const formatValue = (val: any): string => {
  if (val === null || val === undefined || val === '' || val === 0) return '-';
  if (typeof val === 'object') return JSON.stringify(val);
  return String(val);
};

export const formatPackage = (amount: number, currency: string = 'INR'): string => {
  if (!amount) return '-';
  const sym = currency === 'USD' ? '$' : '₹';
  if (currency === 'USD') return `${sym}${amount.toLocaleString()}`;
  if (amount >= 100000) return `${sym}${(amount / 100000).toFixed(2)} LPA`;
  return `${sym}${amount.toLocaleString()}`;
};

export const formatCurrency = (amount: any, currency: string = '₹'): string => {
  if (!amount) return 'N/A';
  if (typeof amount === 'string') return amount;
  if (typeof amount === 'number') {
    if (amount >= 100000) return `${currency}${(amount / 100000).toFixed(1)}L`;
    return `${currency}${amount.toLocaleString()}`;
  }
  return String(amount);
};

export const isRealRank = (v: any): boolean =>
  v !== null && v !== undefined && v !== '' && v !== 0 &&
  String(v).toLowerCase() !== 'n/a' &&
  String(v).toLowerCase() !== 'n/a' &&
  String(v).toLowerCase() !== 'not applicable';
