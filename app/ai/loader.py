import os
import pandas as pd
from langchain_core.documents import Document

# Metadata columns to exclude from page_content embeddings
EXCLUDE_COLUMNS = {
    "faq_id", "created_at", "updated_at", "row_id", "tags", "sr_no", "s_no"
}

def clean_row_to_content(row_series: pd.Series, filename: str = "") -> str:
    """
    Transforms a single CSV row into rich, clean text content for vector indexing.
    Preserves all important semantic fields (e.g. Place Name, Category, Zone, Landmark, Description).
    """
    row_dict = {str(k).strip().lower(): str(v).strip() for k, v in row_series.items() if str(v).strip()}
    
    # 1. Specialized handling for standard FAQ structures (Question & Answer)
    if "question" in row_dict and "answer" in row_dict:
        cat = row_dict.get('category', '')
        cat_prefix = f"Category: {cat}\n" if cat else ""
        return f"{cat_prefix}Question: {row_dict['question']}\nAnswer: {row_dict['answer']}"
    
    # 2. Specialized handling for campus navigation (campus_info.csv)
    if "place_name" in row_dict:
        pid = row_dict.get('place_id', '')
        name = row_dict.get('place_name', '')
        cat = row_dict.get('category', '')
        zone = row_dict.get('zone', '')
        landmark = row_dict.get('landmark', '')
        desc = row_dict.get('description', '')
        lines = []
        if pid: lines.append(f"Place ID: {pid}")
        if name: lines.append(f"Place Name: {name}")
        if cat: lines.append(f"Category: {cat}")
        if zone: lines.append(f"Campus Zone: {zone}")
        if landmark: lines.append(f"Landmark: {landmark}")
        if desc: lines.append(f"Description: {desc}")
        return "\n".join(lines)

    # 3. Specialized handling for campus facilities (facilities.csv)
    if "facility_name" in row_dict:
        fid = row_dict.get('facility_id', '')
        name = row_dict.get('facility_name', '')
        cat = row_dict.get('category', '')
        bldg = row_dict.get('building', '')
        floor = row_dict.get('floor', '')
        loc = row_dict.get('location', '')
        desc = row_dict.get('description', '')
        facs = row_dict.get('facilities', '')
        cap = row_dict.get('capacity', '')
        status = row_dict.get('status', '')
        lines = []
        if fid: lines.append(f"Facility ID: {fid}")
        if name: lines.append(f"Facility Name: {name}")
        if cat: lines.append(f"Category: {cat}")
        if bldg: lines.append(f"Building: {bldg}")
        if floor: lines.append(f"Floor: {floor}")
        if loc: lines.append(f"Location: {loc}")
        if desc: lines.append(f"Description: {desc}")
        if facs: lines.append(f"Amenities & Features: {facs}")
        if cap: lines.append(f"Capacity: {cap}")
        if status: lines.append(f"Status: {status}")
        return "\n".join(lines)

    # 4. Specialized handling for departments (departments.csv)
    if "department_name" in row_dict:
        dept_name = row_dict.get('department_name', '')
        prog = row_dict.get('program', '')
        bldg = row_dict.get('building', '')
        hod = row_dict.get('hod_name', '')
        email = row_dict.get('department_email', '')
        phone = row_dict.get('contact_number', '')
        lines = []
        if dept_name: lines.append(f"Department Name: {dept_name}")
        if prog: lines.append(f"Program: {prog}")
        if bldg: lines.append(f"Building / Wing: {bldg}")
        if hod: lines.append(f"HOD / Head of Department: {hod}")
        if email: lines.append(f"Email: {email}")
        if phone: lines.append(f"Contact: {phone}")
        return "\n".join(lines)

    # 5. Specialized handling for subjects (subject.csv / subjects.csv)
    if "subject_name" in row_dict:
        s_name = row_dict.get('subject_name', '')
        prog = row_dict.get('program', '')
        dept = row_dict.get('department', '')
        year = row_dict.get('year', '')
        sem = row_dict.get('semester', '')
        lines = []
        if s_name: lines.append(f"Subject Name: {s_name}")
        if prog: lines.append(f"Program: {prog}")
        if dept: lines.append(f"Department: {dept}")
        if sem: lines.append(f"Semester: {sem}")
        if year: lines.append(f"Year: {year}")
        return "\n".join(lines)

    # 6. General structured transformation for all other datasets
    row_str_parts = []
    for col, val in row_series.items():
        clean_col = str(col).strip().lower()
        val_str = str(val).strip()
        
        # Skip empty values and excluded internal administrative columns
        if val_str and clean_col not in EXCLUDE_COLUMNS:
            formatted_col = str(col).replace("_", " ").strip().title()
            row_str_parts.append(f"{formatted_col}: {val_str}")

    return "\n".join(row_str_parts)


def load_csv_knowledge_base(knowledge_base_dir: str = None):
    """
    Dynamically finds and loads all CSV files from the knowledge_base directory,
    cleans metadata fields out of page_content, and constructs LangChain Documents.
    """
    # 1. Determine Project Root Directory
    current_file_dir = os.path.dirname(os.path.abspath(__file__))  # app/ai
    project_root = os.path.abspath(os.path.join(current_file_dir, "..", ".."))

    # 2. Resolve target directory path
    if knowledge_base_dir and os.path.isabs(knowledge_base_dir) and os.path.exists(knowledge_base_dir):
        target_dir = knowledge_base_dir
    else:
        target_dir = os.path.join(project_root, "knowledge_base")

    if not os.path.exists(target_dir):
        print(f"[ERROR] Could not locate directory at '{target_dir}'.")
        return []

    print(f"[INFO] Scanning knowledge base directory: {target_dir}")

    documents = []
    csv_files = []

    # 3. Walk through directory and collect all .csv files (including subfolders like faq/)
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.lower().endswith('.csv'):
                csv_files.append(os.path.join(root, file))

    if not csv_files:
        print(f"[WARNING] Found directory '{target_dir}', but no .csv files were detected inside.")
        return documents

    # 4. Convert CSV rows into clean Documents with rich metadata
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        
        # Note: Raw timetable (9,216 rows) is handled deterministically via the in-memory/MongoDB
        # timetable processor (process_timetable_context) to prevent vector index dilution.
        if filename.lower() == "timetable.csv":
            continue

        try:
            # Handle comma and tab-separated CSV/TSV files seamlessly
            try:
                df = pd.read_csv(file_path, dtype=str, sep=None, engine='python')
            except Exception:
                df = pd.read_csv(file_path, dtype=str)
            
            df = df.fillna("")

            for index, row in df.iterrows():
                content = clean_row_to_content(row, filename=filename)

                if not content.strip():
                    continue

                clean_row_keys = {str(k).strip().lower(): str(v).strip() for k, v in row.items()}
                metadata = {
                    "source": filename,
                    "file_path": file_path,
                    "row": index + 1,
                    "faq_id": clean_row_keys.get("faq_id", "N/A"),
                    "category": clean_row_keys.get("category", "General")
                }

                doc = Document(page_content=content, metadata=metadata)
                documents.append(doc)

        except Exception as e:
            print(f"[ERROR] Error reading CSV file {file_path}: {e}")

    print(f"[OK] Successfully loaded {len(documents)} clean documents from {len(csv_files)} knowledge base files.")
    return documents