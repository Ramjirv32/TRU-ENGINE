#!/bin/bash

# Script to run all 9 QUERIES in parallel for Kumaraguru College of Technology
# Stores each response in a separate JSON file

set -e

# Configuration
COLLEGE_NAME="University of Lucknow"
COUNTRY="India"
LOCATION="Lucknow"
API_KEY="34a1d2a034385b46ef853771af21b0270113dbae01021bd548f0309d65a0d264"
OUTPUT_DIR="/home/ramji/Videos/scap/college_scraper/testing"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

echo "🚀 Starting parallel queries for: $COLLEGE_NAME"
echo "📍 Location: $LOCATION, $COUNTRY"
echo "📁 Output: $OUTPUT_DIR"
echo ""

# Function to run a single query and save response
run_query() {
    local query_type="$1"
    local query_prompt="$2"
    local output_file="$OUTPUT_DIR/${query_type}.json"
    
    # Replace placeholders
    local prompt="${query_prompt//\%COLLEGE_NAME\%/$COLLEGE_NAME}"
    prompt="${prompt//\%COUNTRY\%/$COUNTRY}"
    prompt="${prompt//\%LOCATION\%/$LOCATION}"
    
    echo "[$(date '+%H:%M:%S')] 🔄 Running: $query_type..."
    
    # Run curl and save response
    curl -s --get "https://serpapi.com/search" \
        --data-urlencode "engine=google_ai_mode" \
        --data-urlencode "q=$prompt" \
        --data-urlencode "api_key=$API_KEY" > "$output_file.tmp"
    
    # Parse and pretty-print JSON (if valid)
    if jq . "$output_file.tmp" > "$output_file" 2>/dev/null; then
        echo "✅ $query_type - Saved to: $output_file ($(wc -c < $output_file) bytes)"
    else
        # Save as-is if not valid JSON
        mv "$output_file.tmp" "$output_file"
        echo "⚠️  $query_type - Saved (non-JSON) to: $output_file"
    fi
    
    rm -f "$output_file.tmp"
}

# Define all 9 queries
declare -A QUERIES

# QUERIES["basic_info"]="For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified institutional data for the 2026 academic year or the latest available year if 2026 data is not published. Return only valid JSON with the exact fields: college_name, short_name, established, institution_type, country, location, website, about, summary, rankings (nirf_latest, nirf_previous, qs_world, national_rank, state_rank, guessed_data), student_statistics (total_enrollment, ug_students, pg_students, phd_students, annual_intake, male_percent, female_percent, total_ug_courses, total_pg_courses, total_phd_courses, guessed_data), faculty_staff (total_faculty, student_faculty_ratio, phd_faculty_percent, guessed_data), student_history (student_count_comparison_last_3_years with 2026, 2025, 2024, international_students, guessed_data, categorywise_student_comparison_last_3_years: [{\"year\": \"2026\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}, {\"year\": \"2025\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}, {\"year\": \"2024\", \"ug_students\": integer, \"pg_students\": integer, \"phd_students\": integer, \"international_students\": integer, \"domestic_students\": integer, \"male_students\": integer, \"female_students\": integer}]), accreditations (body, grade, year), affiliations, recognition, campus_area, contact_info (phone, email, address), and sources_verified (array of URLs or document names). IMPORTANT: Find actual numerical values from official sources for 2026. For past years (2025=2026-1, 2024=2026-2), provide comparative data if available. Do not use -1 unless data is genuinely unavailable. Provide estimates based on similar institutions if exact data is not found, but mark as guessed_data: true. Do not add any extra text, only JSON."

# QUERIES["ug_programs"]="For %COLLEGE_NAME% in %COUNTRY% (%LOCATION%), search the official website, academic programs directory, and course listings to find undergraduate degree programs (Bachelor's/B.Tech/B.A./B.Sc. programs). Include program names like 'Computer Science', 'Bachelor of Engineering', 'B.A. in Economics', etc. You can also infer programs based on faculty/departments listed on their site. Return valid JSON with this format: { \"ug_programs\": [\"program1\", \"program2\", ...], \"total_count\": number, \"source\": \"url or 'inferred from departments'\" }. Return an empty array if genuinely no data is available."

# QUERIES["pg_programs"]="For %COLLEGE_NAME% in %COUNTRY% (%LOCATION%), search the official website, graduate programs directory, and course listings to find postgraduate degree programs (Master's/M.Tech/M.A./M.Sc./MBA programs offered). Include program names like 'Master of Science in Computer Science', 'M.Tech in Engineering', 'Master's in Economics', etc. You can also infer programs based on faculty/departments listed on their site. Return valid JSON with this format: { \"pg_programs\": [\"program1\", \"program2\", ...], \"total_count\": number, \"source\": \"url or 'inferred from departments'\" }. Return an empty array if genuinely no data is available."

# QUERIES["phd_programs"]="List all officially offered PhD/Doctoral programs at %COLLEGE_NAME%, %COUNTRY% (%LOCATION%), as of 2026. Include only real programs. Do not invent. Return only JSON: { \"phd_programs\": [\"program_name\", ...] }"

QUERIES["departments"]="Return ONLY valid JSON with NO other text. Format: { \"departments\": [\"Department Name 1\", \"Department Name 2\", ...] }. List all academic departments at %COLLEGE_NAME%, %COUNTRY%. Example: Aeronautical Engineering, Civil Engineering, Computer Science, etc."

# QUERIES["programs"]="What are the main academic programs offered at %COLLEGE_NAME% in %COUNTRY% (%LOCATION%)? List the undergraduate, postgraduate, and PhD programs available."

# QUERIES["placements"]="..."

# QUERIES["fees"]="..."

# QUERIES["infrastructure"]="..."

#QUERIES["placements"]="For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), find the latest verified placement data for 2026, 2025, and 2024. Use only official placement reports, latest NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"data_year\": \"2026\", \"sources\": [\"source URL or document name\"], \"placements\": {\"year\": \"2026\", \"highest_package\": real_number, \"average_package\": real_number, \"median_package\": real_number, \"package_currency\": \"LPA\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges, \"placement_rate_percent\": real_percent, \"total_students_placed\": integer, \"total_companies_visited\": integer, \"graduate_outcomes_note\": \"factual note\"}, \"placement_comparison_last_3_years\": [{\"year\":\"2026\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}, {\"year\":\"2025\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}, {\"year\":\"2024\", \"average_package\": real_number, \"employment_rate_percent\": real_percent, \"package_currency\": string}], \"gender_based_placement_last_3_years\": [{\"year\":\"2026\", \"male_placed\": integer, \"female_placed\": integer, \"male_percent\": real_percent, \"female_percent\": real_percent}], \"sector_wise_placement_last_3_years\": [{\"year\":\"2026\", \"sector\": \"sector name\", \"companies\": [\"company names\"], \"percent\": real_percent}], \"top_recruiters\": [\"company names\"], \"placement_highlights\": \"2-3 sentence factual summary\"}. IMPORTANT: Find actual placement statistics from official sources for each year. Do not use -1 unless data is genuinely unavailable. Provide reasonable estimates based on similar institutions if exact data is not found, but mark as guessed_data: true. Always include currency_type field for all monetary values."

#QUERIES["fees"]="For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified fee structure for 2026, 2025, and 2024. Use only official college website, latest NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"data_year\": \"2026\", \"sources\": [\"source URL or document name\"], \"fees\": {\"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"PhD\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\" for Indian colleges, \"USD\" for US colleges, \"GBP\" for UK colleges, \"AUD\" for Australian colleges}, \"hostel_per_year\": real_number}, \"fees_by_year\": [{\"year\": \"2026\", \"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\"}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\"}, \"PhD\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\"}, \"hostel_per_year\": real_number}, {\"year\": \"2025\", \"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\"}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\"}, \"PhD\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\"}, \"hostel_per_year\": real_number}, {\"year\": \"2024\", \"UG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\"}, \"PG\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\"}, \"PhD\": {\"per_year\": real_number, \"total_course\": real_number, \"currency\": \"INR\"}, \"hostel_per_year\": real_number}], \"fees_note\": \"2-3 sentence factual summary\", \"scholarships_detail\": [{\"name\": \"scholarship name\", \"amount\": real_number, \"currency_type\": \"INR\", \"eligibility\": \"eligibility criteria\", \"provider\": \"provider name\"}]}. IMPORTANT: Find actual fee amounts from official sources for each year. Do not use -1 unless data is genuinely unavailable. Provide reasonable estimates based on similar institutions if exact data is not found, but mark as guessed_data: true. Always include currency_type field for all monetary values."

#QUERIES["infrastructure"]="For the college named '%COLLEGE_NAME%', located in %COUNTRY% (%LOCATION%), provide the latest verified infrastructure details and available scholarships. Use only official college website, latest NIRF submissions, AICTE disclosures, or verified education portals. Return only valid JSON with: {\"guessed_data\": false, \"sources_verified\": [\"source URL or document name\"], \"infrastructure\": [{\"facility\": \"facility name\", \"details\": \"facility details\"}], \"hostel_details\": {\"available\": boolean, \"total_capacity\": integer, \"type\": \"hostel type\"}, \"library_details\": {\"total_books\": integer, \"journals\": integer, \"e_resources\": integer, \"area_sqft\": real_number}, \"transport_details\": {\"buses\": integer, \"routes\": integer}, \"scholarships\": [{\"name\": \"scholarship name\", \"amount\": real_number_or_NA, \"currency_type\": \"INR\", \"eligibility\": \"eligibility criteria\", \"provider\": \"provider name\", \"type\": \"merit/need/specific\", \"application_deadline\": \"date_or_NA\"}]}. IMPORTANT: Always include currency_type field for all monetary amounts. List ALL available scholarships including merit-based, need-based, government, private, and international student scholarships. Do not return any extra text, only JSON."

# Run all queries in parallel
for query_type in "${!QUERIES[@]}"; do
    run_query "$query_type" "${QUERIES[$query_type]}" &
done

# Wait for all background jobs to complete
wait

echo ""
echo "✅ All queries completed!"
echo "📊 Results saved in: $OUTPUT_DIR"
echo ""
echo "Files created:"
ls -lh "$OUTPUT_DIR"/*.json 2>/dev/null | awk '{print "  - " $9 " (" $5 ")"}'

echo ""
echo "✨ Done! You can view results:"
for file in "$OUTPUT_DIR"/*.json; do
    if [ -f "$file" ]; then
        echo "  cat $(basename $file)"
    fi
done
