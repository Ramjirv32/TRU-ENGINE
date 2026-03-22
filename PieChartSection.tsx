'use client';

import { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react';
import { useRouter } from 'next/navigation';
import {
  Chart,
  ArcElement,
  Tooltip,
  Legend,
  ChartConfiguration,
  PieController,
  CategoryScale,
  LinearScale
} from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import { API_URL } from '@/lib/config';

Chart.register(
  PieController,
  ArcElement,
  Tooltip,
  Legend,
  ChartDataLabels,
  CategoryScale,
  LinearScale
);

interface PieChartSectionProps {
  searchResults?: any;
  onCollegeDetails?: (collegeData: any) => void;
}

export default forwardRef(function PieChartSection({
  searchResults,
  onCollegeDetails,
}: PieChartSectionProps, ref) {
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstanceRef = useRef<Chart | null>(null);
  const sectionRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const [collegeData, setCollegeData] = useState<any>(searchResults || null);
  const [showDetails, setShowDetails] = useState(false);
  const [universities, setUniversities] = useState<any[]>([]);
  const [countries, setCountries] = useState<any[]>([]);
  const [selectedCountry, setSelectedCountry] = useState('');
  const [selectedUniversity, setSelectedUniversity] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchedCollege, setSearchedCollege] = useState<any>(null);
  const [isSearchMode, setIsSearchMode] = useState(false);
  const [tooltipData, setTooltipData] = useState<{
    visible: boolean;
    label: string;
    value: number;
    color: string;
    x: number;
    y: number;
    centerX: number;
    centerY: number;
    sliceEdgeX: number;
    sliceEdgeY: number;
  } | null>(null);

  useImperativeHandle(ref, () => ({
    autoSelectCollege: (collegeName: string, country?: string, collegeData?: any) => {
      handleCollegeFromSearch(collegeName, country, collegeData);
    }
  }));

  useEffect(() => {
    // Fetch countries list (silently fail if endpoint not available)
    const fetchCountries = async () => {
      try {
        const response = await fetch(`${API_URL}/api/countries`);
        if (!response.ok) return; // 404 is fine — feature not available
        const data = await response.json();
        if (Array.isArray(data)) setCountries(data);
      } catch {
        // Countries feature not available — skip silently
      }
    };
    fetchCountries();
    // NOTE: /ws/countries WebSocket intentionally removed — endpoint not implemented
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;

    const ctx = chartRef.current.getContext('2d');
    if (!ctx) return;

    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy();
    }

    const rotationAnimationPlugin = {
      id: 'rotationAnimation',
      afterDatasetsDraw(chart: any) {
        const ctx = chart.ctx;
        const chartArea = chart.chartArea;
        const centerX = (chartArea.left + chartArea.right) / 2;
        const centerY = (chartArea.top + chartArea.bottom) / 2;

        const meta = chart.getDatasetMeta(0);
        if (meta && meta.controller) {
          const animationProgress = chart.animationStatus?.progress || 1;

          if (animationProgress < 1) {
            ctx.save();
            ctx.globalAlpha = animationProgress;

            ctx.shadowColor = 'rgba(154, 49, 151, 0.5)';
            ctx.shadowBlur = 15 * animationProgress;

            ctx.restore();
          }
        }
      }
    };

    const config: ChartConfiguration = {
      type: 'pie',
      data: {
        labels: [
          'Total Students',
          'Staff',
          'Scholarships',
          'Masters Degree',
          'International Students',
          'Female Students'
        ],
        datasets: [{
          label: 'College Statistics',
          data: [100, 50, 30, 25, 40, 45],
          backgroundColor: [
            'rgba(94, 234, 212, 0.8)',
            'rgba(253, 224, 71, 0.8)',
            'rgba(251, 146, 60, 0.8)',
            'rgba(244, 114, 182, 0.8)',
            'rgba(196, 181, 253, 0.8)',
            'rgba(147, 197, 253, 0.8)'
          ],
          borderColor: [
            'rgba(94, 234, 212, 1)',
            'rgba(253, 224, 71, 1)',
            'rgba(251, 146, 60, 1)',
            'rgba(244, 114, 182, 1)',
            'rgba(196, 181, 253, 1)',
            'rgba(147, 197, 253, 1)'
          ],
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: {
            bottom: 60
          }
        },
        animation: {
          duration: 3000,
          easing: 'easeInOutCubic',
          animateRotate: true,
          animateScale: true,
          delay: (context: any) => {

            return context.dataIndex * 150;
          },
          onComplete: function () {
            console.log('🎨 Pie chart animation completed');
          }
        } as any,
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
            labels: {
              boxWidth: 20,
              padding: 20,
              font: {
                size: 12
              },
              generateLabels: function (chart: any) {
                const data = chart.data;
                if (data.labels && data.labels.length && data.datasets.length) {
                  return data.labels.map((label: string, i: number) => {
                    const value = data.datasets[0].data[i];
                    const bgColor = Array.isArray(data.datasets[0].backgroundColor)
                      ? data.datasets[0].backgroundColor[i]
                      : data.datasets[0].backgroundColor;
                    const bColor = Array.isArray(data.datasets[0].borderColor)
                      ? data.datasets[0].borderColor[i]
                      : data.datasets[0].borderColor;
                    return {
                      text: `${label}: ${value.toLocaleString()}`,
                      fillStyle: bgColor as string,
                      strokeStyle: bColor as string,
                      lineWidth: 2,
                      index: i
                    };
                  });
                }
                return [];
              }
            }
          },
          tooltip: {
            enabled: false,
            external: function (context: any) {
              const { chart, tooltip } = context;

              if (!tooltip || tooltip.opacity === 0) {
                setTooltipData(null);
                return;
              }

              const dataIndex = tooltip.dataPoints[0].dataIndex;
              const dataset = tooltip.dataPoints[0].dataset;
              const label = chart.data.labels[dataIndex];
              const value = dataset.data[dataIndex];
              const color = Array.isArray(dataset.backgroundColor)
                ? dataset.backgroundColor[dataIndex]
                : dataset.backgroundColor;

              const canvas = chart.canvas;
              const rect = canvas.getBoundingClientRect();
              const container = canvas.parentElement;
              const containerRect = container?.getBoundingClientRect();

              if (!containerRect) return;

              const chartArea = chart.chartArea;
              const centerX = (chartArea.left + chartArea.right) / 2;
              const centerY = (chartArea.top + chartArea.bottom) / 2;

              const meta = chart.getDatasetMeta(0);
              const arc = meta.data[dataIndex];

              if (!arc) return;

              const startAngle = arc.startAngle;
              const endAngle = arc.endAngle;
              const midAngle = (startAngle + endAngle) / 2;

              const sliceEdgeRadius = arc.outerRadius;
              const sliceEdgeXCanvas = centerX + Math.cos(midAngle) * sliceEdgeRadius;
              const sliceEdgeYCanvas = centerY + Math.sin(midAngle) * sliceEdgeRadius;

              const tooltipRadius = arc.outerRadius + 120;
              const tooltipXCanvas = centerX + Math.cos(midAngle) * tooltipRadius;
              const tooltipYCanvas = centerY + Math.sin(midAngle) * tooltipRadius;

              const canvasOffsetX = rect.left - containerRect.left;
              const canvasOffsetY = rect.top - containerRect.top;

              setTooltipData({
                visible: true,
                label,
                value,
                color,
                x: tooltipXCanvas + canvasOffsetX,
                y: tooltipYCanvas + canvasOffsetY,
                centerX: centerX + canvasOffsetX,
                centerY: centerY + canvasOffsetY,
                sliceEdgeX: sliceEdgeXCanvas + canvasOffsetX,
                sliceEdgeY: sliceEdgeYCanvas + canvasOffsetY
              });
            }
          },
          datalabels: {
            display: false
          }
        }
      },
      plugins: [ChartDataLabels]
    };

    chartInstanceRef.current = new Chart(ctx, config);

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
      }
    };
  }, []);

  // ── When searchResults prop changes, update pie chart with real data ──────
  useEffect(() => {
    if (!searchResults) return;
    setSearchedCollege(searchResults);
    setIsSearchMode(true);
    setError('');
    setSelectedCountry('');
    setSelectedUniversity('');

    // Update chart with real student statistics from API
    if (chartInstanceRef.current && (searchResults.student_statistics || searchResults.placements_data)) {
      const stats = searchResults.student_statistics;
      const placements = searchResults.placements_data;
      
      let labels: string[] = [];
      let values: number[] = [];

      // 1. Extract from student_statistics (if it exists)
      if (stats) {
        if (Array.isArray(stats)) {
          const { labels: l, values: v } = extractTopStatistics(stats);
          labels = [...l]; values = [...v];
        } else if (typeof stats === 'object') {
          const pairs: [string, string][] = [
            ['UG Students', 'ug_students'],
            ['PG Students', 'pg_students'],
            ['PhD Students', 'phd_students'],
            ['Total Enrollment', 'total_enrollment'],
          ];
          pairs.forEach(([label, key]) => {
            const val = (stats as any)[key];
            if (val && typeof val === 'number' && val > 0) {
              labels.push(label);
              values.push(val);
            }
          });
        }
      }

      // 2. Extract from placements_data
      if (placements?.placements?.total_students_placed) {
        labels.push('Students Placed');
        values.push(placements.placements.total_students_placed);
      }

      if (labels.length > 0) {
        const colors = generateColors(labels.length);
        chartInstanceRef.current.data.labels = labels;
        chartInstanceRef.current.data.datasets[0].data = values;
        chartInstanceRef.current.data.datasets[0].backgroundColor = colors.backgrounds;
        chartInstanceRef.current.data.datasets[0].borderColor = colors.borders;
        chartInstanceRef.current.update('active');
        console.log('📊 Pie chart updated with real data:', labels, values);
      }
    }

    // Scroll into view
    setTimeout(() => {
      if (sectionRef.current) {
        sectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 300);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchResults]);

  // ── Fetch universities when country changes ───────────────────────────────
  useEffect(() => {
    if (selectedCountry) {
      const country = countries.find((c: any) => c.id === selectedCountry);
      if (!country) return;
      if (isSearchMode) return;

      let ws: WebSocket | null = null;

      const fetchUniversities = async () => {
        try {
          setLoading(true);
          const response = await fetch(`${API_URL}/api/colleges-by-country?country=${encodeURIComponent(country.name)}`);
          if (!response.ok) { setLoading(false); return; }
          const data = await response.json();
          setUniversities(data);
          setLoading(false);
        } catch (error) {
          console.warn('Error fetching universities:', error);
          setLoading(false);
        }
      };

      fetchUniversities();

      const wsUrl = `${API_URL.replace(/^http/, 'ws')}/ws/colleges?country=${encodeURIComponent(country.name)}`;

      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('WebSocket connected for country:', country.name);
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);

            if (message.type === 'colleges_update' && message.colleges) {
              setUniversities(message.colleges);
            } else if (message.type === 'new_college' && message.college) {
              setUniversities((prev: any[]) => {
                const exists = prev.find((u: any) => u.id === message.college.id);
                if (!exists) return [...prev, message.college];
                return prev;
              });
            } else if (message.type === 'scraping_update') {
              console.log('⚡ Scraping update for home pie chart:', message.college_name);

              if (message.update_type === 'phase1_complete' && message.data) {
                const stats = message.data;
                const legacyStats = stats.student_statistics || [];

                // If this is the college we just searched or selected
                if (message.college_name === selectedUniversity || (isSearchMode && searchedCollege?.college_name === message.college_name)) {
                  console.log('📊 Updating pie chart with new scraping data');
                  const { labels, values } = extractTopStatistics(legacyStats);

                  if (labels.length > 0 && chartInstanceRef.current) {
                    const colors = generateColors(labels.length);
                    chartInstanceRef.current.data.labels = labels;
                    chartInstanceRef.current.data.datasets[0].data = values;
                    chartInstanceRef.current.data.datasets[0].backgroundColor = colors.backgrounds;
                    chartInstanceRef.current.data.datasets[0].borderColor = colors.borders;
                    chartInstanceRef.current.update('none'); // No animation for live updates to feel snappy
                  }
                }
              }
            }
          } catch (error) {
            console.error('Error processing WebSocket message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error(' WebSocket error:', error);
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
        };
      } catch (error) {
        console.error('Error connecting to WebSocket:', error);
      }

      return () => {
        if (ws) {
          ws.close();
        }
      };
    } else {
      setUniversities([]);
    }
  }, [selectedCountry, countries]);

  const generateColors = (count: number) => {
    const colorPalette = [
      { bg: 'rgba(94, 234, 212, 0.8)', border: 'rgba(94, 234, 212, 1)' },
      { bg: 'rgba(253, 224, 71, 0.8)', border: 'rgba(253, 224, 71, 1)' },
      { bg: 'rgba(251, 146, 60, 0.8)', border: 'rgba(251, 146, 60, 1)' },
      { bg: 'rgba(244, 114, 182, 0.8)', border: 'rgba(244, 114, 182, 1)' },
      { bg: 'rgba(196, 181, 253, 0.8)', border: 'rgba(196, 181, 253, 1)' },
      { bg: 'rgba(147, 197, 253, 0.8)', border: 'rgba(147, 197, 253, 1)' },
      { bg: 'rgba(134, 239, 172, 0.8)', border: 'rgba(134, 239, 172, 1)' },
      { bg: 'rgba(252, 165, 165, 0.8)', border: 'rgba(252, 165, 165, 1)' }
    ];

    return {
      backgrounds: colorPalette.slice(0, count).map(c => c.bg),
      borders: colorPalette.slice(0, count).map(c => c.border)
    };
  };

  const extractTopStatistics = (data: any[]) => {
    const preferredFields = [
      { label: 'Total Students', matcher: (cat: string) => cat.includes('Total students') && !cat.includes('placed') },
      { label: 'Staff', matcher: (cat: string) => cat.includes('Faculty') || cat.includes('Staff') },
      { label: 'Scholarships', matcher: (cat: string) => cat.includes('Scholarship') },
      { label: 'Masters Degree', matcher: (cat: string) => cat.includes('Postgraduate') || cat.includes('PG') },
      { label: 'International Students', matcher: (cat: string) => cat.includes('International students') && !cat.includes('percentage') },
      { label: 'Female Students', matcher: (cat: string) => cat.includes('Female students') },
      { label: 'Students Placed', matcher: (cat: string) => cat.includes('Total students placed') },
      { label: 'Placement Rate %', matcher: (cat: string) => cat.includes('Placement rate') }
    ];

    const result: { labels: string[], values: number[] } = { labels: [], values: [] };
    const usedCategories = new Set<string>();

    preferredFields.forEach(field => {
      const item = data.find((d: any) => field.matcher(d.category));
      if (item && item.value && item.value > 0) {
        result.labels.push(field.label);
        result.values.push(typeof item.value === 'string' ? parseInt(item.value) : item.value);
        usedCategories.add(item.category);
      }
    });

    return {
      labels: result.labels.slice(0, 6),
      values: result.values.slice(0, 6)
    };
  };

  useEffect(() => {
    if (selectedUniversity && chartInstanceRef.current) {
      const university = universities.find(u => u.id === selectedUniversity || u.name === selectedUniversity);

      if (university && university.data) {
        const { labels, values } = extractTopStatistics(university.data);
        const colors = generateColors(labels.length);

        chartInstanceRef.current.data.labels = labels;
        chartInstanceRef.current.data.datasets[0].data = values;
        chartInstanceRef.current.data.datasets[0].backgroundColor = colors.backgrounds;
        chartInstanceRef.current.data.datasets[0].borderColor = colors.borders;
        chartInstanceRef.current.update('active');
      }
    }
  }, [selectedUniversity, universities]);

  const handleCollegeSearchData = (collegeData: any) => {
    setSearchedCollege(collegeData);
    setIsSearchMode(true);
    setError('');
    setSelectedCountry('');
    setSelectedUniversity('');

    if (chartInstanceRef.current && collegeData.student_statistics) {
      const { labels, values } = extractTopStatistics(collegeData.student_statistics);
      const colors = generateColors(labels.length);

      chartInstanceRef.current.data.labels = labels;
      chartInstanceRef.current.data.datasets[0].data = values;
      chartInstanceRef.current.data.datasets[0].backgroundColor = colors.backgrounds;
      chartInstanceRef.current.data.datasets[0].borderColor = colors.borders;
      chartInstanceRef.current.update('active');
    }

    // onCollegeSearch callback (optional, not currently wired)

    setTimeout(() => {
      if (sectionRef.current) {
        sectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 300);

    setTimeout(() => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.update('default');
      }
    }, 1100);
  };

  const handleCountryChange = (countryId: string) => {
    setSelectedCountry(countryId);
    setSelectedUniversity('');
  };

  const handleUniversityChange = (universityId: string) => {
    setSelectedUniversity(universityId);
    if (sectionRef.current) {
      sectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const handleCountryFromSearch = (countryName: string) => {
    const country = countries.find(c => c.name === countryName);
    if (country) {
      handleCountryChange(country.id);
    }
  };

  const handleCollegeFromSearch = (collegeName: string, country?: string, collegeData?: any) => {
    console.log('🔍 handleCollegeFromSearch called:', { collegeName, country, hasData: !!collegeData });

    if (country) {
      let countryObj = countries.find(c =>
        c.name === country ||
        c.name.toLowerCase() === country.toLowerCase()
      );

      if (!countryObj) {
        console.log('📍 Country not in approved list, adding temporarily:', country);
        const tempCountryId = `temp_${country}`;
        const tempCountry = {
          id: tempCountryId,
          name: country
        };
        setCountries(prev => [...prev, tempCountry]);
        countryObj = tempCountry;
      }

      console.log('✅ Found/Created country:', countryObj);

      setSelectedCountry(String(countryObj.id));
      setIsSearchMode(true);
      setSearchedCollege(collegeData);

      const tempCollege = {
        id: collegeName,
        name: collegeName,
        country: country,
        data: collegeData?.student_statistics || []
      };
      setUniversities([tempCollege]);
      setSelectedUniversity(collegeName);

      if (chartInstanceRef.current && collegeData && collegeData.student_statistics) {
        const { labels, values } = extractTopStatistics(collegeData.student_statistics);
        const colors = generateColors(labels.length);

        chartInstanceRef.current.data.labels = labels;
        chartInstanceRef.current.data.datasets[0].data = values;
        chartInstanceRef.current.data.datasets[0].backgroundColor = colors.backgrounds;
        chartInstanceRef.current.data.datasets[0].borderColor = colors.borders;
        chartInstanceRef.current.update('default');
      }

      setTimeout(() => {
        if (sectionRef.current) {
          sectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 300);

      setTimeout(() => {
        if (chartInstanceRef.current) {
          chartInstanceRef.current.update('default');
        }
      }, 1100);

      return;
    }

    const college = universities.find(u => u.name === collegeName);
    if (college) {
      handleUniversityChange(college.id);
    } else {

      setSelectedUniversity(collegeName);
      setIsSearchMode(true);
      setSearchedCollege(collegeData);

      if (chartInstanceRef.current && collegeData && collegeData.student_statistics) {
        const { labels, values } = extractTopStatistics(collegeData.student_statistics);
        const colors = generateColors(labels.length);

        chartInstanceRef.current.data.labels = labels;
        chartInstanceRef.current.data.datasets[0].data = values;
        chartInstanceRef.current.data.datasets[0].backgroundColor = colors.backgrounds;
        chartInstanceRef.current.data.datasets[0].borderColor = colors.borders;
        chartInstanceRef.current.update('active');
      }

      setTimeout(() => {
        if (sectionRef.current) {
          sectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 300);

      setTimeout(() => {
        if (chartInstanceRef.current) {
          chartInstanceRef.current.update('active');
        }
      }, 1100);
    }
  };

  return (
    <section className="section2" ref={sectionRef}>
      <div className="container-fluid p-0">
        <div className="row p-0 align-items-center">
          <div
            className="col-lg-6 col-md-6 gallery_img_section gallery-1 px-5"
            data-aos="fade-up"
            data-aos-easing="ease"
            data-aos-delay="300"
          >
            <div className="section_2_content">
              <h3>One Click. One Pie. All Clarity.</h3>

              { }
              <div className="text-center py-3">
                <span className="text-muted">Select by Country or Search via Modal</span>
              </div>

              { }
              <div className="select_block">
                <div className="select_area" style={{ display: 'flex', gap: '20px', width: '100%' }}>
                  <select
                    id="countrySelect"
                    className="country-select form-control"
                    value={selectedCountry}
                    onChange={(e) => handleCountryChange(e.target.value)}
                    style={{ flex: 1 }}
                  >
                    <option value="">Select Country</option>
                    {countries.map((country) => (
                      <option key={country.id} value={country.id}>
                        {country.name}
                      </option>
                    ))}
                  </select>
                  <select
                    id="universitySelect"
                    className="university-select form-control"
                    value={selectedUniversity}
                    onChange={(e) => handleUniversityChange(e.target.value)}
                    disabled={!selectedCountry || universities.length === 0 || loading}
                    style={{ flex: 1 }}
                  >
                    <option value="">
                      {loading ? 'Loading colleges...' : 'Select College'}
                    </option>
                    {universities.map((university, index) => (
                      <option key={index} value={university.id || university.name}>
                        {university.name}
                      </option>
                    ))}
                    {isSearchMode && selectedUniversity && !universities.find(u => (u.id || u.name) === selectedUniversity) && (
                      <option value={selectedUniversity}>
                        {selectedUniversity} (Searched)
                      </option>
                    )}
                  </select>
                </div>
              </div>
            </div>
          </div>
          <div
            className="col-lg-6 col-md-6 col-sm-12"
            data-aos="fade-up"
            data-aos-easing="ease"
            data-aos-delay="300"
          >
            <div className="section_2_content">
              <div style={{
                height: '500px',
                position: 'relative',
                opacity: 1,
                animation: 'fadeInScale 0.8s ease-in-out forwards',
                animationDelay: '0.3s'
              }}>
                <style>{`
                  @keyframes fadeInScale {
                    from {
                      opacity: 0;
                      transform: scale(0.95);
                    }
                    to {
                      opacity: 1;
                      transform: scale(1);
                    }
                  }
                  
                  .custom-pie-tooltip {
                    position: absolute;
                    background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
                    border: 2px solid;
                    border-radius: 12px;
                    padding: 12px 16px;
                    pointer-events: none;
                    z-index: 1000;
                    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18), 0 6px 12px rgba(0, 0, 0, 0.12);
                    min-width: 190px;
                    backdrop-filter: blur(12px);
                    transition: all 0.2s ease-in-out;
                    white-space: nowrap;
                  }
                  
                  .tooltip-label {
                    font-weight: 600;
                    font-size: 14px;
                    color: #1e293b;
                    margin-bottom: 4px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                  }
                  
                  .tooltip-value {
                    font-size: 18px;
                    font-weight: 700;
                    color: #0f172a;
                    letter-spacing: -0.5px;
                  }
                  
                  .color-indicator {
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    display: inline-block;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                  }
                `}</style>
                <canvas ref={chartRef} id="universityPieChart"></canvas>

                { }
                {tooltipData && tooltipData.visible && (
                  <>
                    <svg
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                        pointerEvents: 'none',
                        zIndex: 999
                      }}
                    >
                      { }
                      <line
                        x1={tooltipData.sliceEdgeX}
                        y1={tooltipData.sliceEdgeY}
                        x2={tooltipData.x}
                        y2={tooltipData.y}
                        stroke="#000000"
                        strokeWidth="6"
                        opacity="0.1"
                        filter="blur(4px)"
                      />
                      { }
                      <line
                        x1={tooltipData.sliceEdgeX}
                        y1={tooltipData.sliceEdgeY}
                        x2={tooltipData.x}
                        y2={tooltipData.y}
                        stroke="#64748b"
                        strokeWidth="2"
                        opacity="0.7"
                        strokeDasharray="4,4"
                      />
                      { }
                      <circle
                        cx={tooltipData.sliceEdgeX}
                        cy={tooltipData.sliceEdgeY}
                        r="4"
                        fill={tooltipData.color}
                        opacity="0.9"
                      />
                      { }
                      <circle
                        cx={tooltipData.x}
                        cy={tooltipData.y}
                        r="5"
                        fill={tooltipData.color}
                        opacity="0.9"
                        stroke="white"
                        strokeWidth="2"
                      />
                    </svg>

                    { }
                    <div
                      className="custom-pie-tooltip"
                      style={{
                        left: `${tooltipData.x}px`,
                        top: `${tooltipData.y}px`,
                        borderColor: tooltipData.color,
                        opacity: 1,
                        animation: 'tooltipFadeIn 0.2s ease-in-out',
                        transform: 'translate(-50%, -50%)'
                      }}
                    >
                      <div className="tooltip-label">
                        <span className="color-indicator" style={{ backgroundColor: tooltipData.color }}></span>
                        {tooltipData.label}
                      </div>
                      <div className="tooltip-value">
                        {tooltipData.value.toLocaleString()}
                      </div>
                    </div>
                  </>
                )}
              </div>

              { }
              {selectedUniversity && (
                <div style={{ textAlign: 'center', marginTop: '20px' }}>
                  <button
                    onClick={() => {
                      const collegeName = isSearchMode && searchedCollege
                        ? searchedCollege.college_name
                        : universities.find(u => (u.id || u.name) === selectedUniversity)?.name || selectedUniversity;
                      router.push(`/college-details/${encodeURIComponent(collegeName)}`);
                    }}
                    style={{
                      background: 'linear-gradient(to right, #9a3197, #e084cd)',
                      color: 'white',
                      border: 'none',
                      padding: '12px 30px',
                      borderRadius: '25px',
                      fontSize: '16px',
                      fontWeight: '500',
                      cursor: 'pointer',
                      boxShadow: '0 4px 15px rgba(154, 49, 151, 0.3)',
                      transition: 'all 0.3s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.boxShadow = '0 6px 20px rgba(154, 49, 151, 0.4)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 4px 15px rgba(154, 49, 151, 0.3)';
                    }}
                  >
                    📊 View Detailed Statistics
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section >
  );
});
