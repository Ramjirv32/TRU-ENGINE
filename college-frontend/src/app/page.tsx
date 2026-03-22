"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Image from "next/image";
import { 
  Search, 
  Bolt, 
  MapPin, 
  School, 
  Building, 
  ExternalLink, 
  TrendingUp, 
  GraduationCap, 
  CircleDollarSign,
  Library,
  Bus,
  Activity
} from "lucide-react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
  Filler,
} from 'chart.js/auto';
import { Bar, Doughnut, Line, Pie } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
  Filler
);

interface CollegeData {
  basic_info?: any;
  programs?: any;
  placements?: any;
  fees?: any;
  infrastructure?: any;
}

export default function Home() {
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [collegeData, setCollegeData] = useState<CollegeData | null>(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("overview");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError("");
    setCollegeData(null);
    
    // Trigger parallel fetches for individual query types
    const types = ["basic_info", "programs", "placements", "fees", "infrastructure"];
    
    try {
      const fetchPromises = types.map(async (type) => {
        try {
          const res = await fetch("http://localhost:5000/api/college", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ college_name: searchQuery.trim(), type: type })
          });
          
          if (res.ok) {
            const data = await res.json();
            setCollegeData(prev => ({ ...prev, ...data }));
          }
        } catch (err) {
          console.error(`Error fetching ${type}:`, err);
        }
      });

      await Promise.all(fetchPromises);
      setActiveTab("overview");
      setLoading(false);
    } catch (err) {
      setError("Unable to connect to service.");
      setLoading(false);
    }
  };

  const quickSearch = (name: string) => {
    setSearchQuery(name);
    setShowSuggestions(false);
    setTimeout(() => handleSearch(), 100);
  };

  // Autosuggest logic
  useEffect(() => {
    const fetchSuggestions = async () => {
      if (searchQuery.length < 2) {
        setSuggestions([]);
        return;
      }
      try {
        const res = await fetch(`http://localhost:5000/api/suggest?q=${encodeURIComponent(searchQuery)}`);
        if (res.ok) {
          const data = await res.json();
          setSuggestions(data);
        }
      } catch (err) {
        console.error("Suggestion error:", err);
      }
    };

    const timeoutId = setTimeout(fetchSuggestions, 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  // Handle click outside suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const formatVal = (val: any, type = "LPA") => {
    if (val === null || val === undefined || val === -1 || val === "N/A" || val === 0) return "N/A";
    const n = parseFloat(val);
    if (isNaN(n)) return val;

    if (type === "LPA") {
      if (n > 100000) return (n / 100000).toFixed(2) + " Cr";
      return n.toFixed(1) + " LPA";
    }
    if (type === "INR") {
      if (n >= 10000000) return (n / 10000000).toFixed(2) + " Cr";
      if (n >= 100000) return (n / 100000).toFixed(2) + " Lakh";
      return n.toLocaleString("en-IN");
    }
    return n.toLocaleString();
  };

  const renderOverview = () => {
    const basic = collegeData?.basic_info || {};
    const stats = basic.student_statistics || {};
    const faculty = basic.faculty_staff || {};
    const rankings = basic.rankings || {};

    const cleanNum = (val: any) => {
      if (typeof val === 'number') return val;
      if (!val || typeof val !== 'string') return 0;
      const cleaned = val.replace(/,/g, '').replace(/[^0-9.]/g, '').trim();
      const num = parseFloat(cleaned);
      return isNaN(num) ? 0 : num;
    };

    const pieData = {
      labels: ['UG', 'PG', 'PhD', 'Intl'],
      datasets: [{
        data: [
          cleanNum(stats.ug_students), 
          cleanNum(stats.pg_students), 
          cleanNum(stats.phd_students), 
          cleanNum(basic.student_history?.international_students || stats.international_students)
        ],
        backgroundColor: ['#2dd4bf', '#facc15', '#f97316', '#818cf8'],
        hoverOffset: 15
      }]
    };

    const genderData = {
      labels: ['Male', 'Female'],
      datasets: [{
        data: [cleanNum(stats.male_percent), cleanNum(stats.female_percent)],
        backgroundColor: ['#60a5fa', '#f472b6'],
        offset: 10
      }]
    };

    return (
      <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 bg-white rounded-2xl shadow-sm border border-slate-100 flex flex-col gap-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Total Enrollment</span>
            <span className="text-3xl font-extrabold text-slate-900">{stats.total_enrollment?.toLocaleString() || "N/A"}</span>
          </div>
          <div className="p-6 bg-white rounded-2xl shadow-sm border border-slate-100 flex flex-col gap-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Female Ratio</span>
            <div className="flex items-center justify-between">
              <span className="text-3xl font-extrabold text-[#f472b6]">{stats.female_percent || "N/A"}%</span>
              <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-[#f472b6]" style={{ width: `${stats.female_percent || 0}%` }}></div>
              </div>
            </div>
          </div>
          <div className="p-6 bg-white rounded-2xl shadow-sm border border-slate-100 flex flex-col gap-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Faculty Strength</span>
            <span className="text-3xl font-extrabold text-indigo-600">{faculty.total_faculty || "N/A"}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <h3 className="text-xl font-bold text-slate-800">Institutional Detail</h3>
            <p className="text-slate-600 leading-relaxed text-sm md:text-base">
              {basic.summary || basic.about || "Fetching detailed summary..."}
            </p>
            <div className="flex flex-wrap gap-2">
              {(() => {
                const accs = basic.accreditations;
                if (!accs) return null;
                const list = Array.isArray(accs) ? accs : [accs];
                return list.map((acc: any, i: number) => (
                  <span key={i} className="px-3 py-1 bg-indigo-50 text-indigo-700 text-xs font-bold rounded-full border border-indigo-100">
                    {acc?.body} - {acc?.grade} ({acc?.year})
                  </span>
                ));
              })()}
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="h-64 flex flex-col items-center">
                <div className="flex-1 w-full"><Pie data={pieData} options={{ maintainAspectRatio: false }} /></div>
                <span className="text-[10px] font-bold text-slate-400 mt-2">STUDENT COMPOSITION</span>
              </div>
              <div className="h-64 flex flex-col items-center">
                <div className="flex-1 w-full"><Doughnut data={genderData} options={{ maintainAspectRatio: false, cutout: '70%' }} /></div>
                <span className="text-[10px] font-bold text-slate-400 mt-2">GENDER RATIO</span>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="p-8 bg-slate-50 rounded-3xl space-y-4">
              <h4 className="font-bold text-slate-800 border-b border-slate-200 pb-2">Verified Rankings</h4>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">NIRF 2025</span>
                  <span className="text-lg font-black text-indigo-600">{rankings.nirf_rank || rankings.nirf_2025 || "N/A"}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">QS World</span>
                  <span className="text-lg font-black text-slate-700">{rankings.qs_world || "N/A"}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">National Rank</span>
                  <span className="text-lg font-black text-slate-700">{rankings.national_rank || "N/A"}</span>
                </div>
              </div>
            </div>
            <div className="space-y-2 px-4">
              <h4 className="font-bold text-slate-800">Recognition</h4>
              <p className="text-sm text-slate-500">{basic.recognition || "Information not available."}</p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderPlacements = () => {
    const p = collegeData?.placements || {};
    const stats = p.placements || {};
    const comp = p.placement_comparison_last_3_years || [];

    const cleanNum = (val: any) => {
      if (typeof val === 'number') return val;
      if (!val || typeof val !== 'string') return 0;
      const cleaned = val.replace(/,/g, '').replace(/[^0-9.]/g, '').trim();
      const num = parseFloat(cleaned);
      return isNaN(num) ? 0 : num;
    };

    const salaryData = {
      labels: ['Highest', 'Average', 'Median'],
      datasets: [{
        label: 'Package (LPA)',
        data: [
          cleanNum(stats.highest_package), 
          cleanNum(stats.average_package), 
          cleanNum(stats.median_package)
        ],
        backgroundColor: ['#10b981', '#3b82f6', '#f59e0b'],
        borderRadius: 8
      }]
    };

    const sortedComp = [...comp].sort((a,b) => cleanNum(a.year) - cleanNum(b.year));
    const trendData = {
      labels: sortedComp.map(c => c.year),
      datasets: [{
        label: 'Avg Package (LPA)',
        data: sortedComp.map(c => cleanNum(c.average_package)),
        borderColor: '#9a3197',
        backgroundColor: 'rgba(154, 49, 151, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 5
      }]
    };

    return (
      <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="p-6 bg-white rounded-3xl border border-slate-100 shadow-sm space-y-4">
            <h4 className="font-bold text-slate-800">Salary Package Analysis</h4>
            <div className="h-64"><Bar data={salaryData} options={{ maintainAspectRatio: false, plugins: { legend: { display: false } } }} /></div>
          </div>
          <div className="p-6 bg-white rounded-3xl border border-slate-100 shadow-sm space-y-4">
            <h4 className="font-bold text-slate-800">Growth Projection</h4>
            <div className="h-64"><Line data={trendData} options={{ maintainAspectRatio: false }} /></div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-8 bg-emerald-50 rounded-2xl border border-emerald-100 flex flex-col gap-1 items-center">
            <span className="text-xs font-black text-emerald-600 uppercase">Avg Package</span>
            <span className="text-3xl font-black text-emerald-800">{formatVal(stats.average_package)}</span>
          </div>
          <div className="p-8 bg-blue-50 rounded-2xl border border-blue-100 flex flex-col gap-1 items-center">
            <span className="text-xs font-black text-blue-600 uppercase">Highest Package</span>
            <span className="text-3xl font-black text-blue-800">{formatVal(stats.highest_package)}</span>
          </div>
          <div className="p-8 bg-amber-50 rounded-2xl border border-amber-100 flex flex-col gap-1 items-center">
            <span className="text-xs font-black text-amber-600 uppercase">Placement %</span>
            <span className="text-3xl font-black text-amber-800">{stats.placement_rate_percent || "N/A"}%</span>
          </div>
        </div>
      </div>
    );
  };

  const renderFees = () => {
    const f = collegeData?.fees || {};
    const fees = f.fees || {};
    const feeByYear = f.fees_by_year || [];

    const cleanNum = (val: any) => {
      if (typeof val === 'number') return val;
      if (!val || typeof val !== 'string') return 0;
      const cleaned = val.replace(/,/g, '').replace(/[^0-9.]/g, '').trim();
      const num = parseFloat(cleaned);
      return isNaN(num) ? 0 : num;
    };

    const distData = {
      labels: ['UG', 'PG', 'Hostel'],
      datasets: [{
        data: [
          cleanNum(fees.UG?.per_year), 
          cleanNum(fees.PG?.per_year), 
          cleanNum(f.hostel_per_year || fees.hostel_per_year)
        ],
        backgroundColor: ['#9a3197', '#0b0a5c', '#e084cd'],
      }]
    };

    return (
      <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
           <div className="p-8 bg-slate-50 rounded-3xl flex flex-col items-center">
              <h4 className="font-bold text-slate-800 mb-6 w-full">Annual Fee Distribution</h4>
              <div className="h-72 w-full"><Doughnut data={distData} options={{ maintainAspectRatio: false }} /></div>
           </div>
           <div className="space-y-6">
              <div className="p-6 bg-white border-4 border-indigo-50 rounded-3xl">
                <h5 className="font-black text-slate-300 text-[10px] uppercase tracking-tighter mb-4">Core Tuition Breakdown</h5>
                <div className="space-y-4">
                  <div className="flex justify-between items-end">
                    <span className="text-slate-500 text-sm">UG (Per Year)</span>
                    <span className="text-2xl font-black text-slate-900">{formatVal(fees.UG?.per_year, "INR")}</span>
                  </div>
                  <div className="flex justify-between items-end">
                    <span className="text-slate-500 text-sm">PG (Per Year)</span>
                    <span className="text-2xl font-black text-slate-900">{formatVal(fees.PG?.per_year, "INR")}</span>
                  </div>
                  <div className="flex justify-between items-end border-t border-slate-100 pt-4 mt-4">
                    <span className="text-slate-500 text-sm">Hostel/Mess</span>
                    <span className="text-2xl font-black text-indigo-600">{formatVal(fees.hostel_per_year, "INR")}</span>
                  </div>
                </div>
              </div>
           </div>
        </div>
      </div>
    );
  };

  const renderPrograms = () => {
    const p = collegeData?.programs || {};
    const ug = p.ug_programs || [];
    const pg = p.pg_programs || [];
    const phd = p.phd_programs || [];
    const depts = p.departments || [];

    return (
      <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-100 rounded-lg text-indigo-600"><GraduationCap className="w-5 h-5" /></div>
              <h4 className="text-xl font-bold text-slate-800">Undergraduate Programs</h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {ug.length > 0 ? ug.map((prog: string, i: number) => (
                <span key={i} className="px-4 py-2 bg-slate-50 border border-slate-100 rounded-xl text-sm font-medium text-slate-600 hover:border-indigo-200 hover:bg-indigo-50 transition-colors">
                  {prog}
                </span>
              )) : <span className="text-slate-400 italic">No UG programs listed.</span>}
            </div>
          </div>

          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg text-amber-600"><GraduationCap className="w-5 h-5" /></div>
              <h4 className="text-xl font-bold text-slate-800">Postgraduate Programs</h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {pg.length > 0 ? pg.map((prog: string, i: number) => (
                <span key={i} className="px-4 py-2 bg-slate-50 border border-slate-100 rounded-xl text-sm font-medium text-slate-600 hover:border-amber-200 hover:bg-amber-50 transition-colors">
                  {prog}
                </span>
              )) : <span className="text-slate-400 italic">No PG programs listed.</span>}
            </div>
          </div>
        </div>

        <div className="p-8 bg-slate-900 rounded-3xl text-white space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/10 rounded-lg text-white"><Building className="w-5 h-5" /></div>
            <h4 className="text-xl font-bold">Academic Departments</h4>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {depts.map((dept: string, i: number) => (
              <div key={i} className="flex items-center gap-2 p-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-colors">
                <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full"></div>
                <span className="text-sm font-medium text-slate-300">{dept}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderInfrastructure = () => {
    const infra = collegeData?.infrastructure || {};
    const facilities = infra.infrastructure || [];
    const hostel = infra.hostel_details || {};
    const library = infra.library_details || {};
    const transport = infra.transport_details || {};

    return (
      <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 bg-white rounded-2xl border border-slate-100 shadow-sm space-y-4">
            <div className="flex items-center gap-3 text-indigo-600">
              <Building className="w-5 h-5" />
              <h4 className="font-bold">Hostel Capacity</h4>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">Boys</span>
                <span className="font-bold">{hostel.boys_capacity || "N/A"}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">Girls</span>
                <span className="font-bold">{hostel.girls_capacity || "N/A"}</span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                <div className="bg-indigo-600 h-full" style={{ width: '70%' }}></div>
              </div>
              <p className="text-[10px] text-slate-400 leading-tight">{hostel.type}</p>
            </div>
          </div>

          <div className="p-6 bg-white rounded-2xl border border-slate-100 shadow-sm space-y-4">
            <div className="flex items-center gap-3 text-emerald-600">
              <Library className="w-5 h-5" />
              <h4 className="font-bold">Library Assets</h4>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">Total Books</span>
                <span className="font-bold">{library.total_books?.toLocaleString() || "N/A"}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">Area (sq.ft)</span>
                <span className="font-bold">{library.area_sqft?.toLocaleString() || "N/A"}</span>
              </div>
              <p className="text-[10px] text-slate-400 leading-tight">{library.journals}</p>
            </div>
          </div>

          <div className="p-6 bg-white rounded-2xl border border-slate-100 shadow-sm space-y-4">
            <div className="flex items-center gap-3 text-amber-600">
              <Bus className="w-5 h-5" />
              <h4 className="font-bold">Transport Network</h4>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">Bus Fleet</span>
                <span className="font-bold">{transport.buses || "N/A"}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">Route Map</span>
                <span className="font-bold text-xs">Active</span>
              </div>
              <p className="text-[10px] text-slate-400 leading-tight">{transport.routes}</p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <h4 className="text-xl font-bold text-slate-800">Campus Facilities</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {facilities.map((f: any, i: number) => (
              <div key={i} className="p-6 bg-slate-50 rounded-2xl hover:bg-white hover:border-indigo-100 hover:shadow-lg transition-all border border-transparent">
                <h5 className="font-bold text-slate-900 mb-2">{f.facility}</h5>
                <p className="text-xs text-slate-500 leading-relaxed">{f.details}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderContent = () => {
    switch(activeTab) {
      case "overview": return renderOverview();
      case "placements": return renderPlacements();
      case "fees": return renderFees();
      case "programs": return renderPrograms();
      case "infrastructure": return renderInfrastructure();
      default: return renderOverview();
    }
  };

  return (
    <div className="min-h-screen bg-white text-slate-900 selection:bg-indigo-100 selection:text-indigo-900">
      {/* Header / Hero */}
      <header className="relative bg-slate-900 py-24 md:py-32 overflow-hidden">
        <div className="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] pointer-events-none"></div>
        <div className="max-w-7xl mx-auto px-6 relative z-10 flex flex-col items-center text-center space-y-8">
          <div className="flex items-center gap-2 px-4 py-1.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-black uppercase tracking-widest rounded-full">
            <Bolt className="w-3 h-3 fill-indigo-400" />
            V2 Intelligence Engine Active
          </div>
          <h1 className="text-5xl md:text-7xl font-black text-white tracking-tight">
            Decode Your <span className="text-indigo-400">Academic</span> Future.
          </h1>
          <p className="max-w-2xl text-lg text-slate-400 font-medium">
            AI-Scraped institutional intelligence. Real-time fee breakdowns, placement trends, and faculty ratios across 50,000+ global colleges.
          </p>

          <form onSubmit={handleSearch} className="w-full max-w-2xl relative flex flex-col md:flex-row gap-3 p-2 bg-slate-800 border border-white/5 rounded-2xl shadow-2xl">
            <div className="flex-1 flex items-center px-4 gap-3 bg-transparent group relative">
              <Search className="w-5 h-5 text-slate-500 group-focus-within:text-indigo-400 transition-colors" />
              <input 
                type="text" 
                placeholder="Search college name (e.g. Stanford University)" 
                className="w-full bg-transparent border-none py-4 text-white font-medium placeholder:text-slate-600 focus:outline-none"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setShowSuggestions(true);
                }}
                onFocus={() => setShowSuggestions(true)}
              />
              
              {/* Suggestions Dropdown */}
              {showSuggestions && suggestions.length > 0 && (
                <div 
                  ref={dropdownRef}
                  className="absolute top-full left-0 right-0 mt-2 bg-slate-800 border border-white/10 rounded-xl shadow-2xl overflow-hidden z-[100] animate-in fade-in zoom-in-95 duration-200"
                >
                  <div className="py-2">
                    {suggestions.map((suggestion, index) => (
                      <button
                        key={index}
                        type="button"
                        onClick={() => quickSearch(suggestion)}
                        className="w-full text-left px-5 py-3 text-slate-300 hover:text-white hover:bg-slate-700/50 flex items-center gap-3 transition-colors border-b border-white/5 last:border-none"
                      >
                        <School className="w-4 h-4 text-indigo-400 opacity-50" />
                        <span className="font-medium text-sm">
                          {(() => {
                            const queryLower = searchQuery.toLowerCase();
                            const index = suggestion.toLowerCase().indexOf(queryLower);
                            if (index === -1) return suggestion;
                            return (
                              <>
                                {suggestion.substring(0, index)}
                                <span className="text-indigo-400 font-black">{suggestion.substring(index, index + searchQuery.length)}</span>
                                {suggestion.substring(index + searchQuery.length)}
                              </>
                            );
                          })()}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <button 
              type="submit" 
              disabled={loading}
              className="px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-black rounded-xl transition-all active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              Search {loading ? <Activity className="w-4 h-4 animate-spin" /> : <Bolt className="w-4 h-4" />}
            </button>
          </form>

          <div className="flex flex-wrap justify-center gap-4 pt-4 opacity-50">
            {/* Trending examples removed as requested */}
          </div>
        </div>
      </header>

      {/* Results Section */}
      <main className="max-w-7xl mx-auto px-6 -mt-12 mb-24 relative z-20">
        {loading && (
          <div className="p-20 bg-white rounded-3xl shadow-2xl border border-slate-100 flex flex-col items-center justify-center space-y-6">
            <div className="w-16 h-16 border-4 border-indigo-100 border-t-indigo-600 rounded-full animate-spin"></div>
            <div className="text-center">
              <h2 className="text-2xl font-black text-slate-800 tracking-tight">Ingesting Educational Data</h2>
              <p className="text-slate-500 font-medium">Scraping official records & real-time search proxies...</p>
            </div>
          </div>
        )}

        {collegeData && collegeData.basic_info && (
          <div className="space-y-8 animate-in fade-in duration-700">
            {/* College Header Card */}
            <div className="p-8 md:p-12 bg-white rounded-3xl shadow-2xl border border-slate-100 flex flex-col md:flex-row justify-between items-start gap-8">
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-indigo-600 font-black text-sm uppercase">
                  <MapPin className="w-4 h-4" />
                  {collegeData.basic_info.location || "N/A"}, {collegeData.basic_info.country || "N/A"}
                </div>
                <h2 className="text-4xl md:text-6xl font-black text-slate-900 tracking-tighter">
                  {collegeData.basic_info.college_name || searchQuery}
                </h2>
                <div className="flex flex-wrap gap-6 text-slate-500 font-bold text-sm">
                  <div className="flex items-center gap-2"><School className="w-4 h-4" /> Est. {collegeData.basic_info.established || "N/A"}</div>
                  <div className="flex items-center gap-2"><Building className="w-4 h-4" /> {collegeData.basic_info.institution_type || "Institution"}</div>
                </div>
              </div>
              {collegeData.basic_info.website && collegeData.basic_info.website !== 'N/A' && (
                <a 
                  href={collegeData.basic_info.website.startsWith('http') ? collegeData.basic_info.website : `https://${collegeData.basic_info.website}`} 
                  target="_blank" 
                  className="px-6 py-3 bg-slate-50 hover:bg-slate-100 text-slate-700 font-bold rounded-xl flex items-center gap-2 border border-slate-200 transition-all active:scale-95"
                >
                  Visit Official <ExternalLink className="w-4 h-4" />
                </a>
              )}
            </div>

            {/* Content Tabs */}
            <div className="flex gap-2 p-1 bg-slate-50 rounded-2xl border border-slate-200 overflow-x-auto no-scrollbar">
              {["overview", "programs", "placements", "fees", "infrastructure"].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 min-w-[120px] px-6 py-3 rounded-xl font-black text-xs uppercase tracking-widest transition-all ${activeTab === tab ? "bg-slate-900 text-white shadow-lg" : "text-slate-400 hover:text-slate-600 hover:bg-slate-200/50"}`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Main Panel */}
            <div className="p-8 md:p-12 bg-white rounded-3xl shadow-2xl border border-slate-100 min-h-[500px]">
              {renderContent()}
            </div>
          </div>
        )}

        {error && (
            <div className="p-8 bg-red-50 border border-red-200 text-red-700 rounded-3xl font-bold flex items-center gap-4">
                <Bolt className="w-6 h-6 rotate-180" />
                {error}
            </div>
        )}
      </main>

      <footer className="max-w-7xl mx-auto px-6 py-12 border-t border-slate-100 text-center space-y-4">
        <p className="text-slate-400 font-bold text-xs uppercase tracking-widest">
          © 2026 College Intelligence Dashboard | Verified via Serper & Google AI
        </p>
        <div className="flex justify-center gap-8 text-xs font-black text-indigo-600 uppercase">
          <a href="#">Terms</a>
          <a href="#">Privacy</a>
          <a href="#">API Documentation</a>
        </div>
      </footer>
    </div>
  );
}
