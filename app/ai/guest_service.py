"""
app/ai/guest_service.py
Dedicated Guest Mode Service for SVIT-AI Assistant.
Enforces the Guest Access Rule:
  GUEST: Access ONLY to 11 Public SVIT Information Categories
  STUDENT: 11 Public SVIT Information Categories + Existing Student Features

11 Public Categories:
1. About SVIT
2. Available Courses
3. Fees Structure
4. Admission Process
5. Eligibility Criteria
6. Seats Available
7. Timing (College & Office)
8. Events & Activities
9. Bus Facilities & Routes
10. Central Library
11. Sports & Gymnasium

Official SVIT Website: https://svitvasad.ac.in/
"""

import re
from typing import Tuple, Optional, Dict, Any, List

# ==============================================================================
# 11 PUBLIC SVIT INFORMATION CATEGORIES (Verified Official SVIT Vasad Data)
# ==============================================================================

PUBLIC_CATEGORIES_METADATA = [
    {
        "id": "about_svit",
        "name": "About SVIT",
        "icon": "school",
        "description": "History, PKM Trust, AICTE approval, GTU affiliation & campus overview",
        "sample_query": "Tell me about SVIT Vasad, PKM Trust, and the campus"
    },
    {
        "id": "courses",
        "name": "Available Courses",
        "icon": "book-open",
        "description": "B.E., M.E., MCA, B.Arch, and Diploma Engineering programs",
        "sample_query": "What courses and degree programs are available at SVIT?"
    },
    {
        "id": "fees",
        "name": "Fees Structure",
        "icon": "credit-card",
        "description": "FRC Gujarat approved fee structure & government scholarships (MYSY)",
        "sample_query": "What is the fees structure and scholarships for B.E. and MCA?"
    },
    {
        "id": "admission",
        "name": "Admission Process",
        "icon": "user-plus",
        "description": "ACPC centralized admission steps, merit list, and counseling",
        "sample_query": "What is the admission process for engineering at SVIT Vasad?"
    },
    {
        "id": "eligibility",
        "name": "Eligibility Criteria",
        "icon": "check-circle",
        "description": "10+2 HSC Science requirements, GUJCET/JEE, and D2D criteria",
        "sample_query": "What is the eligibility criteria for admission in B.E.?"
    },
    {
        "id": "seats",
        "name": "Seats Available",
        "icon": "users",
        "description": "Intake capacity across Computer, IT, AI-ML, Mechanical, Civil, etc.",
        "sample_query": "How many seats are available in each branch at SVIT?"
    },
    {
        "id": "timing",
        "name": "College & Office Timings",
        "icon": "clock",
        "description": "Academic hours, administrative section, accounts, and library timings",
        "sample_query": "What are the college, administrative office, and library timings?"
    },
    {
        "id": "events",
        "name": "Events & Fests",
        "icon": "sparkles",
        "description": "PRAKARSHT (Tech Fest), SPANDAN (Cultural), AVAHAN (Sports), & Hackathons",
        "sample_query": "What events, techfests, and cultural activities are held at SVIT?"
    },
    {
        "id": "bus",
        "name": "Bus Facilities",
        "icon": "bus",
        "description": "20+ college bus routes across Vadodara, Anand, Nadiad, and timings",
        "sample_query": "What bus facilities and routes are available for students?"
    },
    {
        "id": "library",
        "name": "Central Library",
        "icon": "library",
        "description": "50,000+ books, reading hall, e-library terminals, and digital resources",
        "sample_query": "Tell me about the Central Library, reading room, and book facilities"
    },
    {
        "id": "sports",
        "name": "Sports & Gymnasium",
        "icon": "trophy",
        "description": "Cricket ground, indoor badminton courts, modern gym, and sports week",
        "sample_query": "What sports grounds, indoor games, and gym facilities are available?"
    }
]

# Pre-compiled Category Responses with rich, authoritative Markdown
CATEGORY_RESPONSES = {
    "about_svit": (
        "### 🏛️ About SVIT Vasad (Sardar Vallabhbhai Patel Institute of Technology)\n\n"
        "**Sardar Vallabhbhai Patel Institute of Technology (SVIT)**, Vasad was established in **1997** "
        "by **The New English School Trust (NEST)** as a tribute to the great national leader **Sardar Vallabhbhai Patel**, "
        "with the noble mission of imparting high-quality technical education in Gujarat.\n\n"
        "#### 📜 Institutional History & Founding:\n"
        "* **Founding Leadership**: The Trust requested **Prof. Shantibhai Amin**, a philanthropic-administrator, to take the responsibility of establishing the college as **Chairman of the Board of Management**, supported by **Shri Shivabhai Patel** and eminent educationists and technocrats of the region.\n"
        "* **1997 Genesis**: Started with three conventional engineering disciplines — **Civil Engineering (60 seats)**, **Mechanical Engineering (60 seats)**, and **Electrical Engineering (60 seats)**, approved by AICTE New Delhi and affiliated with Gujarat University (now GTU).\n"
        "* **Expansion Milestones**: \n"
        "  - **1998**: Introduced **Computer Engineering** and **Information Technology** (+80 intake).\n"
        "  - **1999**: Introduced **Electronics & Communication Engineering** (40 intake).\n"
        "  - **2003**: Introduced **MCA (Master of Computer Applications)**.\n"
        "* **Managing Trust**: Managed by **The New English School Trust (NEST)** / **Prajapati Kelavani Mandal (PKM)** (Trust Reg. No. E-274 Kheda).\n"
        "* **Institutional Leadership Today**: Guided by **Principal & Professor Dr. D. P. Soni**.\n\n"
        "#### 🎯 Official Vision Statement:\n"
        "> *\"To be an excellent academic institute by imparting quality technical education to the prospective engineers and carve them into value added technocrats who seek professional excellence, nation building and social responsibility.\"*\n\n"
        "#### 🚀 Official Mission Statements (6 Core Pillars):\n"
        "1. **Institution of Repute**: To be known as an institution of repute safeguarding societal and national interest.\n"
        "2. **Faculty Excellence**: To cultivate adaptability and groom faculty members with changing trends in their fields by giving them opportunities to upgrade.\n"
        "3. **Societal & Industry Alignment**: To constantly align and orient as per societal needs by delivering knowledge on contemporary themes in accordance with job potential.\n"
        "4. **Student-Centric Environment**: To facilitate a student–centric environment and offer them industrial and practical exposure.\n"
        "5. **Research & Innovation**: To adopt appropriate processes and practices in the field of education, research and innovation to prepare students for professional challenges.\n"
        "6. **Ethical Values & Sardar Patel Ideals**: To offer robust co-curricular & extra-curricular activity support to inculcate ethical values, right attitude and sound professionalism, following the ideals of Sardar Patel.\n\n"
        "#### 📍 Scenic Campus & Location:\n"
        "* **Campus Size**: **26 lush green acres** located on the serene banks of the **River Mahisagar** at Vasad, Anand district, Gujarat.\n"
        "* **Connectivity**: Behind Vasad Railway Station, Vasad - 388306. Strategically situated right on the NH-48 corridor between Vadodara (~18 km) and Anand (~20 km).\n"
        "* **Infrastructure**: High-tech computer centers, specialized mechanical workshops, civil material labs, 50,000+ volume Central Library, auditorium, bank counter, and student amenities.\n\n"
        "#### 📞 Official Contact & Helplines:\n"
        "* 📞 **Engineering (B.E., M.E., MCA, D.Voc)**: `+91-9510782981 / 82` | `+91-9510782983 / 84`\n"
        "* 💼 **Training & Placement Cell**: `+91-9316770768`\n"
        "* 🏛️ **Architecture & Interior Design**: `+91-9510782985`\n"
        "* 📧 **Official Email**: `principal@svitvasad.ac.in`\n\n"
        "#### 🌐 Official SVIT Portals & Web Links:\n"
        "* 🏠 **Official Website Home**: [https://svitvasad.ac.in/Home/Index/index.html](https://svitvasad.ac.in/Home/Index/index.html)\n"
        "* 📜 **About Us Portal**: [https://svitvasad.ac.in/Engineering/AboutUs/index.html](https://svitvasad.ac.in/Engineering/AboutUs/index.html)\n"
        "* 🏛️ **The College (Board of Management & Chairman's Message)**: [https://svitvasad.ac.in/Home/TheCollege/index.html](https://svitvasad.ac.in/Home/TheCollege/index.html)\n"
        "* 🏢 **Central Facilities**: [https://svitvasad.ac.in/Home/Facilities/index.html](https://svitvasad.ac.in/Home/Facilities/index.html)\n"
        "* 💼 **Placement & Career**: [https://svitvasad.ac.in/Home/Placement/index.html](https://svitvasad.ac.in/Home/Placement/index.html)\n"
        "* 🎓 **Admissions Portal**: [https://svitvasad.ac.in/Home/Admissions/index.html](https://svitvasad.ac.in/Home/Admissions/index.html)\n"
        "* 💳 **Online Fees Payment (SVIT ERP)**: [https://sviterp.com/](https://sviterp.com/)\n"
        "* 🤝 **SVIT Alumni Portal**: [https://alumni.svitvasad.ac.in/](https://alumni.svitvasad.ac.in/)"
    ),

    "courses": (
        "### 📚 Academic Programs & Courses Offered at SVIT Vasad\n\n"
        "SVIT Vasad offers AICTE-approved undergraduate, postgraduate, and diploma engineering programs affiliated with GTU:\n\n"
        "#### 1. Undergraduate Programs (B.E. / B.Tech — 4 Years):\n"
        "* 💻 **Computer Engineering (CE)**\n"
        "* 🌐 **Information Technology (IT)**\n"
        "* 🤖 **Artificial Intelligence & Machine Learning (AI & ML)**\n"
        "* 📊 **Data Science**\n"
        "* ⚙️ **Mechanical Engineering**\n"
        "* 🏗️ **Civil Engineering**\n"
        "* ⚡ **Electrical Engineering**\n"
        "* 📡 **Electronics & Communication (EC)**\n\n"
        "#### 2. Postgraduate Programs (M.E. & MCA):\n"
        "* 🖥️ **Master of Computer Applications (MCA)** — 2 Years\n"
        "* 🔬 **M.E. in Computer Engineering** (Software Engineering) — 2 Years\n"
        "* 🌉 **M.E. in Civil Engineering** (Structural Engineering) — 2 Years\n"
        "* 🏭 **M.E. in Mechanical Engineering** (CAD / CAM) — 2 Years\n\n"
        "#### 3. Diploma Engineering Programs (3 Years):\n"
        "* Computer Engineering, Information Technology, Mechanical, Civil, Electrical, and Automobile Engineering.\n\n"
        "#### 4. Architecture:\n"
        "* 🏛️ **B.Arch (Bachelor of Architecture)** — 5-Year degree offered through the SVIT College of Architecture.\n\n"
        "🌐 Official Details: [https://svitvasad.ac.in/Home/Index/index.html](https://svitvasad.ac.in/Home/Index/index.html)"
    ),

    "fees": (
        "### 💰 SVIT Vasad Fees Structure & Scholarships\n\n"
        "The fee structure at SVIT Vasad is strictly regulated and approved by the **Fee Regulatory Committee (FRC) — Technical**, Government of Gujarat.\n\n"
        "#### 💵 Indicative Annual Tuition Fees (Per Academic Year):\n"
        "* **Bachelor of Engineering (B.E. / B.Tech)**: Approx. **₹73,000 – ₹78,000 / year** *(as sanctioned by FRC Gujarat)*\n"
        "* **Master of Computer Applications (MCA)**: Approx. **₹70,000 – ₹75,000 / year**\n"
        "* **Master of Engineering (M.E.)**: Approx. **₹72,000 – ₹75,000 / year**\n"
        "* **Diploma Engineering**: Approx. **₹42,000 – ₹45,000 / year**\n\n"
        "*(Note: Official fees are subject to periodic revision by FRC Gujarat. Examination and university enrollment fees are paid separately as per GTU regulations).* \n\n"
        "#### 💳 Online Fees Payment Portal:\n"
        "* Students and parents can pay college fees online through the **SVIT ERP Portal**: [https://sviterp.com/](https://sviterp.com/)\n\n"
        "#### 🎓 Government Scholarships & Financial Aid:\n"
        "* **MYSY (Mukhyamantri Yuva Swavalamban Yojana)**: 50% tuition fee subsidy (up to ₹50,000/year) for eligible students with ≥80 percentile in 10+2 and family income ≤ ₹6 LPA.\n"
        "* **Digital Gujarat Scholarships**: Full/partial fee reimbursement for SC / ST / SEBC / NT-DNT / EWS category students.\n"
        "* **AICTE Pragati & Saksham Schemes**: ₹50,000/year for female students and differently-abled students.\n"
        "* **Trust Concessions**: Merit-cum-means financial aid supported by Prajapati Kelavani Mandal (PKM) Trust."
    ),

    "admission": (
        "### 🎓 SVIT Vasad Admission Process\n\n"
        "Admissions to SVIT Vasad are transparent and merit-based, conducted centrally through Government of Gujarat regulatory committees:\n\n"
        "#### 📋 Step-by-Step Degree Engineering (B.E.) Admission:\n"
        "1. **ACPC Centralized Registration**: After 12th Science and GUJCET results, register online on the official ACPC Gujarat portal: [https://jacpcldce.ac.in/](https://jacpcldce.ac.in/).\n"
        "2. **Document Verification**: Complete online document verification and receive your ACPC state merit rank.\n"
        "3. **Choice Filling (Mock & Actual Rounds)**: Log in and select **Sardar Vallabhbhai Patel Institute of Technology (SVIT), Vasad** and your desired branches (e.g., Computer, IT, AI & ML) in your preference list.\n"
        "4. **Seat Allotment**: ACPC publishes Round 1 & Round 2 allotment results based on your merit percentile and branch choices.\n"
        "5. **Fee Token & Reporting**: Pay the online token admission fee through ACPC to confirm your seat, download the allotment letter, and report to the SVIT Vasad campus student section for final admission confirmation.\n\n"
        "#### 🔗 Official SVIT Admissions Portal:\n"
        "* For official college admission circulars, vacant quota notices, and branch seats, visit: [https://svitvasad.ac.in/Home/Admissions/index.html](https://svitvasad.ac.in/Home/Admissions/index.html)\n\n"
        "#### 🏫 Management & Vacant Quota:\n"
        "* Vacant seats remaining after ACPC online rounds are filled strictly as per ACPC guidelines through institute-level merit notices published on [https://svitvasad.ac.in/](https://svitvasad.ac.in/).\n\n"
        "#### 📌 Other Programs:\n"
        "* **Diploma**: Centralized via ACPDC ([https://acpdc.co.in](https://acpdc.co.in)).\n"
        "* **MCA & M.E.**: Centralized via ACPC based on CMAT / Gujarat PGCET."
    ),

    "eligibility": (
        "### 📋 Admission Eligibility Criteria at SVIT Vasad\n\n"
        "Eligibility norms are aligned with AICTE, GTU, and ACPC Gujarat regulations:\n\n"
        "#### 1. Bachelor of Engineering (B.E. — 1st Year):\n"
        "* **Educational Qualification**: Passed 10+2 (Standard XII / HSC Science Stream) from Gujarat Secondary & Higher Secondary Education Board (GSEB), CBSE, ICSE, or equivalent recognized board.\n"
        "* **Mandatory Subjects**: Physics and Mathematics (or Biology for eligible bio-branches) along with Chemistry / Computer Science / Information Technology / Biotechnology / Technical Vocational subject.\n"
        "* **Minimum Qualifying Marks**:\n"
        "  * **General / Open Category**: Minimum **45% marks** in theory & practical of PCM.\n"
        "  * **Reserved Categories (SC / ST / SEBC / EWS)**: Minimum **40% marks**.\n"
        "* **Competitive Exam**: Must possess a valid rank/score in **GUJCET** (Gujarat Common Entrance Test) or **JEE (Main)**.\n\n"
        "#### 2. D2D (Direct Second Year B.E.):\n"
        "* Passed 3-year Diploma in relevant branch with minimum 45% (40% for reserved category) as recognized by GTU/TEB.\n\n"
        "#### 3. Master of Computer Applications (MCA):\n"
        "* Passed BCA / B.Sc (Computer Science / IT) or Bachelor's Degree with Mathematics at 10+2 or degree level with minimum 50% marks (45% for reserved category) + valid score in **CMAT**.\n\n"
        "#### 4. Master of Engineering (M.E.):\n"
        "* Recognized B.E. / B.Tech in relevant branch with minimum 50% (45% for reserved category) + valid score in **GATE** or **Gujarat PGCET**."
    ),

    "seats": (
        "### 🪑 SVIT Vasad Seats Available (Branch-wise Intake Capacity)\n\n"
        "SVIT Vasad has an annual intake capacity of **over 1,200+ students** across all engineering, computer application, and diploma programs:\n\n"
        "| Program & Branch | Duration | Annual Approved Intake |\n"
        "| :--- | :---: | :---: |\n"
        "| 💻 **B.E. Computer Engineering** | 4 Years | **120 Seats** |\n"
        "| 🌐 **B.E. Information Technology** | 4 Years | **120 Seats** |\n"
        "| 🤖 **B.E. Artificial Intelligence & Machine Learning (AI & ML)** | 4 Years | **60 Seats** |\n"
        "| 📊 **B.E. Data Science** | 4 Years | **60 Seats** |\n"
        "| ⚙️ **B.E. Mechanical Engineering** | 4 Years | **60 Seats** |\n"
        "| 🏗️ **B.E. Civil Engineering** | 4 Years | **60 Seats** |\n"
        "| ⚡ **B.E. Electrical Engineering** | 4 Years | **60 Seats** |\n"
        "| 📡 **B.E. Electronics & Communication (EC)** | 4 Years | **60 Seats** |\n"
        "| 🖥️ **MCA (Master of Computer Applications)** | 2 Years | **60 Seats** |\n"
        "| 🔬 **M.E. Specializations** (Computer / Civil / Mechanical) | 2 Years | **18 Seats each** |\n"
        "| 🛠️ **Diploma Engineering Branches** | 3 Years | **60 Seats each** |\n\n"
        "*Seat reservation policy follows Gujarat Government norms for SC, ST, SEBC/OBC, EWS, TFWS (Tuition Fee Waiver Scheme), and physically disabled candidates.*"
    ),

    "timing": (
        "### ⏰ SVIT Vasad College, Office & Facility Timings\n\n"
        "The standard operational timings of SVIT Vasad campus are as follows:\n\n"
        "#### 🏫 Academic Hours:\n"
        "* **Monday to Friday**: **08:30 AM to 04:30 PM**\n"
        "* **Working Saturdays**: **08:30 AM to 01:30 PM** *(Alternate Saturdays / extra practical sessions / student club activities)*\n"
        "* **Sundays & Public Holidays**: Closed\n\n"
        "#### 🏢 Administrative & Office Timings:\n"
        "* **Principal Secretariat & Registrar Office**: 09:00 AM to 05:00 PM (Monday to Friday)\n"
        "* **Student Section & Inquiries**: 09:00 AM to 04:30 PM\n"
        "* **Accounts Office & Fee Collection Counter**: 09:30 AM to 03:30 PM\n"
        "* **Transport & Bus Pass Office**: 08:00 AM to 04:30 PM\n\n"
        "#### 📖 Campus Facilities Timings:\n"
        "* **Central Library**: **08:30 AM to 06:00 PM** (Reading hall remains open until 07:00 PM during mid-term and GTU exam periods)\n"
        "* **Central Canteen**: **08:00 AM to 06:00 PM**\n"
        "* **Sports Complex & Gymnasium**: 06:30 AM – 08:00 AM (Morning) & 04:30 PM – 06:30 PM (Evening)"
    ),

    "events": (
        "### 🎪 Events, Tech Fests & Activities at SVIT Vasad\n\n"
        "SVIT Vasad has an active campus life with state- and national-level events throughout the academic year:\n\n"
        "#### 🌟 Major Flagship Festivals:\n"
        "1. 🚀 **PRAKARSHT (National Tech Fest)**:\n"
        "   * SVIT's flagship annual national-level technical festival attracting 5,000+ students from all over Gujarat and India.\n"
        "   * Features 40+ competitions: Hackathons, Robo-Wars, Robo-Soccer, Code Mania, Circuit Design, Bridge Craft, CAD Modeling, and Technical Paper Presentations.\n\n"
        "2. 🎭 **SPANDAN (Annual Cultural Fest)**:\n"
        "   * The vibrant annual cultural festival featuring music concerts, inter-college dance competitions, street plays, fashion shows, fine arts, photography exhibitions, and live celebrity performances.\n\n"
        "3. 🏆 **AVAHAN (Annual Sports Championship)**:\n"
        "   * Week-long inter-department sports tournament with Cricket, Football, Volleyball, Basketball, Badminton, Table Tennis, Chess, and Athletics track events.\n\n"
        "#### 💡 Workshops, Hackathons & Seminars:\n"
        "* **HackSVIT**: 36-hour non-stop hackathon for solving industry & societal problems using AI, IoT, and Cloud.\n"
        "* **IEEE & CSI Student Chapter Events**: Hands-on workshops on Cloud Computing, Web3, Machine Learning, and Cyber Security.\n"
        "* **Community & NSS Activities**: Annual Blood Donation Camps, Tree Plantation Drives, and Rural Digital Literacy Programs."
    ),

    "bus": (
        "### 🚌 SVIT Vasad Bus Facilities & Transportation Routes\n\n"
        "SVIT Vasad operates an extensive fleet of **20+ dedicated college buses** providing convenient and safe daily transportation for students and staff across Central Gujarat.\n\n"
        "#### 📍 Major Bus Routes Covered:\n"
        "* **Vadodara City Network** (15+ buses):\n"
        "  * **Routes**: Tarsali, Manjalpur, Makarpura, Alkapuri, Nizampura, Fatehgunj, Subhanpura, Gotri, Karelibaug, Waghodia Road, Ajwa Road, Harni, Sama, Atladara, Vasna Road, Chhani, and Ellora Park.\n"
        "* **Anand & Vallabh Vidyanagar**:\n"
        "  * **Routes**: Anand City, Borsad, Petlad, Khambhat, and Vallabh Vidyanagar.\n"
        "* **Nadiad & Umreth**:\n"
        "  * **Routes**: Nadiad Highway, Uttarsanda, Vaso, Chaklasi, and Umreth.\n\n"
        "#### ⏱️ Timings & Operation:\n"
        "* **Morning Pickup**: Between **06:30 AM and 07:45 AM** depending on your pickup stop.\n"
        "* **Campus Arrival**: All buses arrive at SVIT Vasad campus between **08:15 AM and 08:25 AM**.\n"
        "* **Evening Departure**: Buses leave campus sharp at **04:30 PM** (Monday to Friday) and **01:30 PM** (Working Saturdays).\n\n"
        "#### 🎫 Bus Pass Registration:\n"
        "* Managed by the **Transport Office** located adjacent to the Main Campus Gate.\n"
        "* Contact: `transport@svitvasad.ac.in` | Phone: `02692-274766`"
    ),

    "library": (
        "### 📖 SVIT Central Library & Learning Resource Center\n\n"
        "The Central Library at SVIT Vasad is a state-of-the-art knowledge hub located centrally in the Academic Complex.\n\n"
        "#### 📚 Collection & Facilities:\n"
        "* **Books & Volumes**: Extensive repository of **50,000+ printed books** and **15,000+ distinct textbook and reference titles** covering all branches of engineering, computer applications, and basic sciences.\n"
        "* **Journals & Periodicals**: Subscriptions to 70+ national and international print journals and magazines.\n"
        "* **Digital Library & E-Resources**: 30+ high-speed computer terminals providing direct access to IEEE Xplore, ScienceDirect, DELNET, NPTEL video lectures, and GTU past exam papers.\n"
        "* **Air-Conditioned Reading Hall**: Spacious, serene reading environment accommodating **250+ students** simultaneously.\n"
        "* **Automation & Circulation**: Fully automated using **SOUL** library management software with barcoded identity cards for rapid book issue and return.\n\n"
        "#### ⏰ Library Working Hours:\n"
        "* **Monday to Friday**: **08:30 AM to 06:00 PM**\n"
        "* **Reading Room (Exam Period)**: Open till **07:00 PM**\n"
        "* **Saturday**: 08:30 AM to 02:00 PM"
    ),

    "sports": (
        "### ⚽ Sports, Gymnasium & Fitness Facilities at SVIT Vasad\n\n"
        "SVIT Vasad prioritizes holistic student growth through expansive outdoor and indoor athletic facilities across a **5-acre dedicated sports zone**:\n\n"
        "#### 🏏 Outdoor Grounds:\n"
        "* **Cricket Ground**: Full-sized cricket ground with turf and practice nets.\n"
        "* **Football Field**: Standard lush green football pitch.\n"
        "* **Basketball Court**: Concrete basketball court with tournament floodlighting.\n"
        "* **Volleyball & Throwball**: Dual outdoor sandy volleyball courts.\n"
        "* **Athletics Track**: 200-meter running track, long jump pit, and shot put arena.\n\n"
        "#### 🏸 Indoor Sports Complex:\n"
        "* **Badminton**: Two standard indoor courts with wooden flooring.\n"
        "* **Table Tennis**: Multiple tournament-grade TT boards.\n"
        "* **Mind Games**: Dedicated halls for Chess and Carrom clubs.\n\n"
        "#### 🏋️ Modern Fitness Gymnasium:\n"
        "* Fully equipped air-cooled gym with motorized treadmills, elliptical trainers, cross-trainers, dumbbells, bench presses, and multi-gym workout stations under the guidance of a qualified physical training instructor.\n"
        "* **Gym Timings**: 06:30 AM – 08:00 AM (Morning) & 04:30 PM – 06:30 PM (Evening).\n\n"
        "SVIT teams actively participate and consistently win laurels in the annual **GTU Spirit Sports Tournaments** and inter-university meets.\n\n"
        "#### 🏢 Central Facilities Portal:\n"
        "* For details on all sports arenas, gym, and grounds, visit: [https://svitvasad.ac.in/Home/Facilities/index.html](https://svitvasad.ac.in/Home/Facilities/index.html)"
    ),

    "placement": (
        "### 💼 SVIT Vasad Training & Placement Cell\n\n"
        "SVIT Vasad has a highly active Training & Placement Cell that prepares students for corporate careers and conducts campus placement drives with top global companies.\n\n"
        "#### 🌟 Placement Highlights & Top Recruiters:\n"
        "* **Top Recruiters**: TCS, Infosys, L&T, Reliance Industries, Adani Group, Cognizant, Wipro, Capgemini, Torrent Power, Polycab, MG Motors, and eInfochips.\n"
        "* **Salary Packages**: Highest salary package reaching **₹12 – ₹15 LPA** with an average package of **₹3.5 – ₹5.5 LPA**.\n"
        "* **Training Programs**: Technical coding bootcamps, mock aptitude tests, group discussions, and expert career guidance.\n\n"
        "#### 🔗 Official Placement & Career Portal:\n"
        "* 💼 **Placement Portal**: [https://svitvasad.ac.in/Home/Placement/index.html](https://svitvasad.ac.in/Home/Placement/index.html)\n"
        "* 📞 **Placement Officer**: `+91-9316770768` | `placement@svitvasad.ac.in`"
    ),

    "facilities": (
        "### 🏢 Central Facilities & Campus Infrastructure at SVIT Vasad\n\n"
        "SVIT Vasad features comprehensive, world-class facilities across its 26-acre campus on the banks of River Mahisagar:\n\n"
        "#### 📌 Central Facilities Overview:\n"
        "* 📖 **Central Library**: 50,000+ volumes, IEEE digital resources, and 250+ capacity reading hall.\n"
        "* 💻 **Computing Labs**: Modern computer laboratories with high-speed internet connectivity.\n"
        "* ⚙️ **Engineering Workshops**: Advanced mechanical, civil, electrical, and electronics practical labs.\n"
        "* ☕ **Central & Diploma Canteens**: Clean, hygienic food courts for students and staff.\n"
        "* ⚽ **5-Acre Sports Zone**: Cricket ground, indoor badminton courts, modern gymnasium, and basketball courts.\n"
        "* 🏦 **Campus Amenities**: Bank counter, student stationery store, medical first-aid room, and 24x7 security.\n\n"
        "#### 🔗 Official Central Facilities Portal:\n"
        "* 🏢 **Central Facilities Portal**: [https://svitvasad.ac.in/Home/Facilities/index.html](https://svitvasad.ac.in/Home/Facilities/index.html)"
    )
}

# ==============================================================================
# 2. KEYWORD MATCHER & INTENT ROUTER FOR 11 CATEGORIES
# ==============================================================================

CATEGORY_KEYWORDS = {
    "about_svit": [
        "about svit", "about institute", "about the institute", "about the institution",
        "svit vasad", "pkm", "prajapati kelavani mandal", "trust", "principal", "dr. d. p. soni",
        "d. p. soni", "history", "established", "campus area", "acres", "river mahisagar",
        "mahisagar", "gtu affiliation", "aicte approval", "overview of svit", "who is principal",
        "tell me about svit", "where is svit", "svit website", "official website",
        "vision", "mission", "vision and mission", "vision & mission", "aim", "objective", "objectives",
        "nest", "new english school", "new english school trust",
        "shantibhai", "shantibhai amin", "prof shantibhai amin", "shivabhai", "shivabhai patel",
        "the college", "thecollege", "board of management", "founding chairman", "chairman", "chairman message",
        "leadership", "founder", "founders",
        "alumni", "alumni portal", "alumni network", "home page", "official home",
        "mandatory disclosure", "contact number", "phone number", "helpline", "phone", "helpline number",
        "history of svit", "how svit was founded", "who founded svit", "why svit was named"
    ],
    "courses": [
        "course", "courses", "available course", "available courses", "branch", "branches",
        "programs", "programmes", "degrees", "degree", "b.e", "be course", "be courses",
        "btech", "m.e", "me course", "mca", "diploma", "b.arch", "architecture",
        "engineering courses", "computer engineering", "information technology", "ai ml",
        "data science", "civil engineering", "mechanical engineering", "electrical engineering",
        "what can i study", "specialization", "departments"
    ],
    "fees": [
        "fee", "fees", "fee structure", "fees structure", "tuition fee", "cost of study",
        "frc", "frc fee", "scholarship", "scholarships", "mysy", "digital gujarat",
        "how much is fee", "fee for be", "fee for mca", "fee for diploma", "payment",
        "annual fee", "yearly fee", "concession", "financial aid",
        "sviterp", "sviterp.com", "online fees", "fee portal", "pay fee", "pay fees", "pay online"
    ],
    "admission": [
        "admission", "admissions", "admission process", "how to apply", "how to get admission",
        "how can i get admission", "acpc", "acpdc", "gujcet", "merit list", "choice filling",
        "seat allotment", "reporting", "vacant quota", "management quota", "counseling",
        "application form", "admission procedure", "steps for admission", "apply online",
        "admission link", "admission portal", "admissions page", "apply link"
    ],
    "placement": [
        "placement", "placements", "career", "campus placement", "recruiter", "recruiters",
        "training and placement", "job", "jobs", "salary package", "highest package", "placement portal"
    ],
    "facilities": [
        "facilities", "facility", "central facilities", "campus facilities", "infrastructure portal"
    ],
    "eligibility": [
        "eligibility", "eligible", "eligibility criteria", "cut off", "cutoff",
        "minimum marks", "percentage required", "qualification", "qualifying marks",
        "12th marks", "10+2 marks", "pcm percentage", "d2d eligibility", "mca eligibility"
    ],
    "seats": [
        "seat", "seats", "seats available", "seat matrix", "intake", "intake capacity",
        "number of seats", "how many seats", "computer seats", "it seats", "ai ml seats",
        "mech seats", "civil seats", "capacity", "total seats"
    ],
    "timing": [
        "timing", "timings", "college timing", "college timings", "college hours", "office hours",
        "office hour", "college time", "office timing", "office timings", "opening time",
        "closing time", "working hours", "when does college open", "when does college close",
        "working days", "saturday timing", "admin office timing", "accounts timing",
        "library timing", "operating hours", "hours"
    ],
    "events": [
        "event", "events", "fest", "fests", "prakarsht", "spandan", "avahan",
        "techfest", "tech fest", "tech fests", "cultural fest", "sports fest",
        "hackathon", "hacksvit", "symposium", "annual day", "workshop", "workshops",
        "activities", "celebrations", "college events", "college fest", "college fests"
    ],
    "bus": [
        "bus", "buses", "bus route", "bus routes", "bus facility", "bus facilities",
        "transport", "transportation", "pickup point", "bus stop", "commute",
        "bus timing", "bus pass", "vadodara bus", "anand bus", "nadiad bus", "college bus"
    ],
    "library": [
        "library", "central library", "reading room", "books", "book collection",
        "e-library", "delnet", "journals", "digital library", "library rules",
        "borrow book", "issue book", "reading hall"
    ],
    "sports": [
        "sport", "sports", "gym", "gymnasium", "ground", "playground", "cricket",
        "football", "badminton", "table tennis", "basketball", "volleyball",
        "indoor games", "outdoor games", "athletics", "fitness", "sports complex"
    ]
}

# Queries strictly reserved for registered students / faculty
RESTRICTED_STUDENT_PATTERNS = [
    r'\b(?:my\s+)?timetable\b',
    r'\b(?:my\s+)?time\s*table\b',
    r'\b(?:my\s+)?lecture\s*schedule\b',
    r'\b(?:my\s+)?class\s*schedule\b',
    r'\bwhat\s*(?:is\s*)?my\s*(?:next\s*)?class\b',
    r'\bwhere\s*(?:is\s*)?my\s*(?:next\s*)?class\b',
    r'\bnext\s*class\b',
    r'\bclass\s*right\s*now\b',
    r'\bwhere\s*do\s*i\s*go\s*now\b',
    r'\b(?:my\s+)?attendance\b',
    r'\b(?:my\s+)?result\b',
    r'\b(?:my\s+)?marks\b',
    r'\b(?:my\s+)?exam\s*(?:seat|roll|hall\s*ticket)\b',
    r'\bmid[- ]?term\s*(?:marks|score|exam\s*date)\b',
    r'\bstudent\s*notice(?:s)?\b',
    r'\b(?:internal\s+)?circular(?:s)?\b',
    r'\bcircular(?:s)?\s*for\s*(?:div|batch|semester|sem)\b',
    r'\b(?:my\s+)?profile\b',
    r'\b(?:my\s+)?enrollment\s*(?:no|number)?\b',
    r'\b(?:my\s+)?roll\s*number\b',
    r'\bwho\s*teaches\s*(?:batch|div|division)\b',
    r'\bfaculty\s*(?:meeting|notes|record|records|circular|phone|mobile|salary|personal)\b',
    r'\bchange\s*(?:my\s*)?(?:batch|div|division|password)\b'
]

# Greetings and Small Talk (Allowed for both Guest and Student)
GREETING_PATTERNS = [
    r'^(?:hi|hello|hey|hola|namaste|greetings)\b',
    r'^(?:good\s*morning|good\s*afternoon|good\s*evening)\b',
    r'\b(?:who\s*are\s*you|what\s*are\s*you|what\s*is\s*your\s*name|what\s*can\s*you\s*do|help\s*me)\b',
    r'^(?:thank\s*you|thanks|thx)\b',
    r'^(?:bye|goodbye|see\s*you)\b'
]

# ==============================================================================
# 3. GUEST QUERY CLASSIFIER & RESPONSE GENERATOR
# ==============================================================================

def is_word_match(text: str, keyword: str) -> bool:
    """Accurate word-boundary keyword check."""
    if not text or not keyword:
        return False
    return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))


def classify_guest_query(user_query: str) -> Dict[str, Any]:
    """
    Evaluates a user query under the Guest Access Rule.
    Returns:
      {
        "is_guest_allowed": bool,
        "matched_category": str or None,
        "is_greeting": bool,
        "is_restricted": bool,
        "response_text": str or None,
        "followup_suggestions": list
      }
    """
    query = user_query.strip().lower()

    # 1. Check for Greetings / Small Talk
    for pat in GREETING_PATTERNS:
        if re.search(pat, query):
            guest_welcome = (
                "Hello! 👋 Welcome to **SVIT AI Assistant (Guest Mode)**.\n\n"
                "I can provide official public information about **SVIT Vasad** across these 11 categories:\n"
                "1. 🏛️ **About SVIT**\n"
                "2. 📚 **Available Courses**\n"
                "3. 💰 **Fees Structure**\n"
                "4. 🎓 **Admission Process**\n"
                "5. 📋 **Eligibility Criteria**\n"
                "6. 🪑 **Seats Available**\n"
                "7. ⏰ **College & Office Timings**\n"
                "8. 🎪 **Events & Tech Fests**\n"
                "9. 🚌 **Bus Facilities & Routes**\n"
                "10. 📖 **Central Library**\n"
                "11. ⚽ **Sports & Gymnasium**\n\n"
                "*(Note: For personalized class timetables, attendance, and student notices, please [Sign In](/login) or [Register](/register)).*\n\n"
                "How can I help you explore SVIT today?"
            )
            return {
                "is_guest_allowed": True,
                "matched_category": "greeting",
                "is_greeting": True,
                "is_restricted": False,
                "response_text": guest_welcome,
                "followup_suggestions": [
                    "Tell me about SVIT Vasad 🏛️",
                    "What courses are available? 📚",
                    "Show fees structure 💰",
                    "What is the admission process? 🎓"
                ]
            }

    # 2. Check for Restricted Student Features FIRST
    # (e.g., "my timetable", "my next class", "my attendance", "my marks")
    is_restricted = any(re.search(pat, query) for pat in RESTRICTED_STUDENT_PATTERNS)
    if is_restricted:
        restriction_message = (
            "🔒 **Access Restricted to Registered Students & Faculty**\n\n"
            "This information is available for registered students and faculty only. "
            "(Such as personal timetables, ongoing lectures, student attendance, marks, and internal circulars).\n\n"
            "👉 Please **[Sign In](/login)** or **[Register](/register)** with your student account to access personalized academic features.\n\n"
            "---\n\n"
            "### 🌐 As a **Guest**, you have full access to these 11 public categories:\n"
            "1. 🏛️ **About SVIT** — Campus history, PKM Trust, approvals, and leadership\n"
            "2. 📚 **Available Courses** — B.E., M.E., MCA, B.Arch, and Diploma programs\n"
            "3. 💰 **Fees Structure** — FRC Gujarat approved fee structures and government scholarships (MYSY)\n"
            "4. 🎓 **Admission Process** — ACPC online registration, choice filling, and counseling steps\n"
            "5. 📋 **Eligibility Criteria** — Minimum 10+2 Science / GUJCET / JEE qualifications\n"
            "6. 🪑 **Seats Available** — Branch-wise intake capacity and seat allocation\n"
            "7. ⏰ **Timing** — Academic hours, administrative section, and library timings\n"
            "8. 🎪 **Events** — PRAKARSHT (Tech Fest), SPANDAN (Cultural), and AVAHAN (Sports)\n"
            "9. 🚌 **Bus Facilities** — 20+ routes covering Vadodara, Anand, and Nadiad\n"
            "10. 📖 **Central Library** — 50,000+ books, digital lab, and reading hall\n"
            "11. ⚽ **Sports & Gym** — Cricket ground, indoor badminton, and fitness gym"
        )
        return {
            "is_guest_allowed": False,
            "matched_category": None,
            "is_greeting": False,
            "is_restricted": True,
            "response_text": restriction_message,
            "followup_suggestions": [
                "Tell me about SVIT Vasad 🏛️",
                "What courses are available? 📚",
                "Show fees structure 💰",
                "What bus facilities are available? 🚌"
            ]
        }

    # 3. Match against the 11 Public Categories
    matched_cat = None
    max_matches = 0

    for cat_id, keywords in CATEGORY_KEYWORDS.items():
        cat_score = 0
        for kw in keywords:
            if is_word_match(query, kw):
                # Multi-word specific intent phrases carry much higher priority
                words_count = len(kw.split())
                cat_score += (words_count * 3) if words_count > 1 else 1
        if cat_score > max_matches:
            max_matches = cat_score
            matched_cat = cat_id

    if matched_cat and max_matches > 0:
        ans = CATEGORY_RESPONSES.get(matched_cat)
        # Select related suggestions
        all_cats = [c["sample_query"] for c in PUBLIC_CATEGORIES_METADATA if c["id"] != matched_cat]
        suggestions = all_cats[:4]

        return {
            "is_guest_allowed": True,
            "matched_category": matched_cat,
            "is_greeting": False,
            "is_restricted": False,
            "response_text": ans,
            "followup_suggestions": suggestions
        }

    # 4. If query does not match any of the 11 categories and is not greeting:
    # Under the GUEST ACCESS RULE: The Guest user should have access ONLY to these 11 categories.
    fallback_restriction = (
        "🔒 **Access Restricted to Registered Students & Faculty**\n\n"
        "This information is available for registered students and faculty only. "
        "As a **Guest**, your access is focused on official public SVIT information across 11 designated categories.\n\n"
        "👉 Please **[Sign In](/login)** or **[Register](/register)** for full student features.\n\n"
        "### 🌟 You can ask me anything about:\n"
        "* 🏛️ **About SVIT Vasad**\n"
        "* 📚 **Available Courses**\n"
        "* 💰 **Fees Structure**\n"
        "* 🎓 **Admission Process**\n"
        "* 📋 **Eligibility Criteria**\n"
        "* 🪑 **Seats Available**\n"
        "* ⏰ **College & Office Timings**\n"
        "* 🎪 **Events & Techfests**\n"
        "* 🚌 **Bus Facilities**\n"
        "* 📖 **Central Library**\n"
        "* ⚽ **Sports & Gym Facilities**"
    )
    return {
        "is_guest_allowed": False,
        "matched_category": None,
        "is_greeting": False,
        "is_restricted": True,
        "response_text": fallback_restriction,
        "followup_suggestions": [
            "What courses are offered? 📚",
            "What is the fees structure? 💰",
            "How does the admission process work? 🎓",
            "Tell me about the bus facilities 🚌"
        ]
    }
