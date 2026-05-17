Requirements Document
1. Application Overview
Application Name: Call Dashboard Reporter

Description: A web application that ingests call records from business phone systems, normalizes and stores the data, and displays agent performance metrics through an interactive dashboard. The application must be demo-ready and deployable within 3 days.

2. Users and Usage Scenarios
Target Users:

Call center managers (admin/manager roles)
Operations supervisors (admin/manager roles)
Call center agents (agent role)
Business analysts monitoring phone system performance
Core Usage Scenarios:

Upload historical call records from PBX systems for analysis (admin/manager only)
Monitor real-time agent performance rankings (all roles)
Track call volume trends and patterns (all roles)
Review import history and data quality (admin/manager only)
3. Page Structure and Functionality
3.1 Page Hierarchy
Call Dashboard Reporter
├── Main Section (all roles)
│   ├── Overview (default page)
│   └── Leaderboard
└── Settings Section (admin/manager only)
    ├── Upload CSV
    └── Import History
3.2 Common Elements
Navigation Bar:

Application name displayed at top
Persistent sidebar with links organized into sections
Active page indicator
Visual separator between Main and Settings sections
Settings section label displayed above Settings pages
Role switcher in sidebar footer for demo purposes
Role Switcher:

Located at bottom of sidebar
Dropdown or button group with three options: Admin, Manager, Agent
Clicking a role immediately switches the user's role
Navigation menu updates to show/hide Settings section based on selected role
Current role is visually indicated
Navigation Visibility Rules:

Agent role: sees only Overview and Leaderboard in navigation
Admin role: sees Overview, Leaderboard, and Settings section (Upload CSV, Import History)
Manager role: sees Overview, Leaderboard, and Settings section (Upload CSV, Import History)
Settings section is completely hidden from sidebar when role is Agent
3.3 Page Details
3.3.1 Overview Page
Route: /

Access: All roles (admin, manager, agent)

Summary Cards Section:

Display four metric cards:
Calls Today: total call count for current day
Calls This Week: total call count for current week (Monday to Sunday)
Calls This Month: total call count for current month
Top Agent Today: name and call count of highest-performing agent today
Call Volume Chart:

Bar chart showing calls per hour for today (24 hours)
X-axis: hours (0-23)
Y-axis: call count
Top Agents Table:

Display top 5 agents for today
Columns: Rank, Agent Name, Answered Calls
Sorted by answered calls descending
Auto-refresh:

Page data refreshes every 30 seconds
Display "Last updated" timestamp
3.3.2 Leaderboard Page
Route: /leaderboard

Access: All roles (admin, manager, agent)

Period Selector:

Three toggle buttons: Daily, Weekly, Monthly
Default selection: Daily
Clicking a button loads corresponding period data
Period Definitions:

Daily: today 00:00 to 23:59
Weekly: current week Monday 00:00 to Sunday 23:59
Monthly: 1st day of current month to last day of current month
Leaderboard Table:

Display up to 50 agents ranked by performance
Columns:
Rank: position in leaderboard
Agent: agent extension and name
Total Calls: all calls handled
Answered: successfully answered calls
Missed: unanswered calls
Avg Talk Time: average duration of answered calls (in minutes)
Answer Rate: percentage of answered calls out of total calls
Ranking logic: sort by answered calls descending, then by total talk time descending
Visual indicators: display medal icons for ranks 1-3 (gold, silver, bronze)
Table is sortable by clicking any column header
Auto-refresh:

Data refreshes every 60 seconds
3.3.3 Upload CSV Page
Route: /upload

Access: Admin and manager roles only

File Upload Zone:

Drag-and-drop area accepting CSV files only
Alternative "Browse" button for file selection
Visual feedback when file is dragged over zone
Upload Process:

User selects or drops a CSV file
File is sent to backend for processing
System detects PBX format automatically
System parses and imports call records
System deduplicates records to avoid double-counting
Result Display:

After upload completes, show result card with:
Detected PBX system type
Number of rows successfully imported
Number of rows skipped (duplicates)
Original filename
Display success state (green) or error state (red)
If error occurs, show clear error message
Supported PBX Formats:

3CX: identified by headers "Call ID", "Ring Duration", "Dialed Number", "Reason"
Yeastar: identified by headers "CallFrom", "CallTo", "Talk Duration", "Disposition"
FreePBX: identified by headers "src", "dst", "duration", "disposition", "accountcode"
Unsupported Format Handling:

If CSV headers do not match any known format, reject file
Display error message listing the headers found in the file
3.3.4 Import History Page
Route: /history

Access: Admin and manager roles only

Import Log Table:

Display last 20 import operations, newest first
Columns:
Filename: original CSV filename
PBX Detected: detected PBX system type
Rows In: number of rows imported
Rows Skipped: number of duplicate rows skipped
Status: success or error badge (green for success, red for error)
Time: timestamp of import operation
If import failed, clicking the row shows error message details
Auto-refresh:

Table refreshes every 30 seconds
4. Data Model
4.1 Call Records
Each call record contains:

Unique identifier
Caller phone number (required)
Caller name
Callee phone number (required)
Callee name
Call start time (required, indexed)
Call answer time
Call end time
Total duration in seconds
Ring duration in seconds
Call direction: inbound, outbound, internal, or unknown
Call outcome: answered, missed, abandoned, busy, voicemail, or unknown
Queue name (indexed)
Agent extension (indexed)
Agent name
DID number (direct inward dial)
PBX source system (required)
Row hash for deduplication (unique)
Import timestamp
4.2 Import Log
Each import operation records:

Auto-incrementing identifier
Filename
File hash for duplicate file detection (unique)
PBX source system
Number of rows imported
Number of rows skipped
Status: pending, success, or error
Error message (if applicable)
Processing timestamp
5. Business Rules and Logic
5.1 Role-Based Access Control
Role Definitions:

Admin: full access to all pages including Settings section
Manager: full access to all pages including Settings section
Agent: access only to Overview and Leaderboard pages
Access Enforcement:

When user attempts to navigate to /upload or /history with agent role, system redirects to / (Overview page)
Display access denied message after redirect
Settings section is hidden from navigation sidebar when role is agent
Role switcher allows demo users to change roles without login system
5.2 File Import Process
Format Detection:

System examines CSV headers to identify PBX format
If headers match a known format, corresponding parser is used
If no match found, import is rejected with error message
Data Parsing:

Each row is parsed according to detected PBX format
Field values are normalized to standard format
Invalid rows are skipped and counted
Deduplication:

Before storing any record, system computes a hash of all field values
If hash already exists, record is skipped (not an error)
Duplicate count is tracked and reported
File Tracking:

Each uploaded file's hash is stored
If same file is uploaded again, system skips processing
Import log records all attempts
5.3 Automated File Watching
Folder Monitoring:

System monitors a designated folder for new CSV files
Scan occurs every 60 seconds
Only files with .csv extension are processed
Processing Flow:

System checks if file hash already exists in import log
If new file, system imports it automatically
After successful import, file is moved to a "processed" subfolder
Import result is logged
Scheduling:

Folder scan runs continuously every 60 seconds
Scan starts automatically when application launches
5.4 Data Retention
Automatic Purge:

System deletes call records older than 365 days
Purge runs daily at 02:00
Only affects call records, not import logs
5.5 Leaderboard Calculation
Metrics Computation:

Total Calls: count of all calls where agent was involved
Answered Calls: count of calls with outcome = answered
Missed Calls: count of calls with outcome = missed
Total Talk Time: sum of duration for all answered calls
Average Talk Time: total talk time divided by answered calls
Answer Rate: (answered calls / total calls) × 100%
Ranking Logic:

Primary sort: answered calls descending
Secondary sort: total talk time descending
Rank assigned as position in sorted list
5.6 API Endpoints
The application provides the following data access points:

Upload Endpoint:

Accepts CSV file upload
Requires admin or manager role
Returns: detected PBX type, rows imported, rows skipped, filename
Leaderboard Endpoint:

Accepts period parameter: daily, weekly, or monthly
Accessible to all roles
Returns: ranked list of agents with all performance metrics
Import History Endpoint:

Requires admin or manager role
Returns: last 20 import log entries, newest first
Overview Stats Endpoint:

Accessible to all roles
Returns: total calls today, total calls this week, total calls this month, top agent today (name and count), number of active agents today
Health Check Endpoint:

Returns: application status indicator
6. Exception and Boundary Cases
Scenario	Handling
Agent role attempts to access /upload	Redirect to / with access denied message
Agent role attempts to access /history	Redirect to / with access denied message
Agent role directly enters restricted URL	Redirect to / with access denied message
Role switcher changes from admin to agent	Navigation updates immediately, Settings section disappears
Role switcher changes from agent to admin	Navigation updates immediately, Settings section appears
CSV file with unknown headers	Reject file, display error message listing found headers
CSV file with missing required fields	Skip invalid rows, count as skipped, continue processing
Duplicate file uploaded	Skip processing, return previous import result
Duplicate call records in same file	Skip duplicates, count as skipped
Empty CSV file	Accept file, report 0 rows imported
Malformed CSV (parsing error)	Reject file, display parsing error message
No agents have calls in selected period	Display empty leaderboard table with message
File upload during folder scan	Both processes handle independently, deduplication prevents conflicts
Database connection failure	Display error message, retry on next operation
Very large CSV file (10,000+ rows)	Process normally, may take longer, show progress if possible
7. Acceptance Criteria
User opens application with role switcher set to "Agent" and sees only Overview and Leaderboard in navigation sidebar
User switches role to "Admin" using role switcher in sidebar footer
Settings section appears in navigation with Upload CSV and Import History pages
User navigates to Upload CSV page and drops a 3CX format CSV file into upload zone
System displays result card showing "3CX detected", number of rows imported, and number of rows skipped
User navigates to Leaderboard page and selects "Daily" period
System displays ranked table with agent names, call counts, and performance metrics
User switches role back to "Agent" using role switcher
Settings section disappears from navigation, user attempts to manually navigate to /upload
System redirects to Overview page and displays access denied message
8. Features Not Included in This Release
User authentication or login system
Persistent role assignment (roles reset on page refresh)
Settings configuration page
Real-time data push to external analytics platforms (Power BI integration)
WebSocket-based live updates
Call recording playback
Agent scheduling or shift management
Custom report builder
Email notifications for import failures
Multi-language support
Call quality metrics (jitter, latency, packet loss)
Customer satisfaction ratings
Call transcription or sentiment analysis
Export functionality for leaderboard data
Historical trend comparison across periods
Agent-level drill-down pages
Call detail records (CDR) search interface
Automatic file format detection training
Bulk file upload (multiple files at once)
File upload progress bar
Configurable retention period through UI
Role management interface
Audit log for role changes
Permission customization per role
