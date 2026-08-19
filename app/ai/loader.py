import os
import pandas as pd
from langchain_core.documents import Document

# Metadata columns to exclude from page_content embeddings
EXCLUDE_COLUMNS = {
    "faq_id", "id", "keywords", "category", "created_at", 
    "updated_at", "row_id", "tags", "sr_no", "s_no"
}

def clean_row_to_content(row_series: pd.Series) -> str:
    """
    Transforms a single CSV row into clean, student-facing text content,
    excluding internal IDs, keywords, and metadata.
    """
    row_dict = {str(k).strip().lower(): str(v).strip() for k, v in row_series.items() if str(v).strip()}
    
    # 1. Specialized handling for standard FAQ structures (Question & Answer)
    if "question" in row_dict and "answer" in row_dict:
        return f"Question: {row_dict['question']}\nAnswer: {row_dict['answer']}"
    
    # 2. General structured transformation for other datasets (canteen, events, timetable, faculty)
    row_str_parts = []
    for col, val in row_series.items():
        clean_col = str(col).strip().lower()
        val_str = str(val).strip()
        
        # Skip empty values and administrative metadata columns
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
        print(f"❌ Error: Could not locate directory at '{target_dir}'.")
        return []

    print(f"📁 Scanning knowledge base directory: {target_dir}")

    documents = []
    csv_files = []

    # 3. Walk through directory and collect all .csv files (including subfolders like faq/)
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.lower().endswith('.csv'):
                csv_files.append(os.path.join(root, file))

    if not csv_files:
        print(f"⚠️ Warning: Found directory '{target_dir}', but no .csv files were detected inside.")
        return documents

    # 4. Convert every CSV row into a clean Document with metadata
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        try:
            df = pd.read_csv(file_path, dtype=str)
            df = df.fillna("")

            for index, row in df.iterrows():
                # Extract cleaned content string without FAQ IDs / Keywords
                content = clean_row_to_content(row)

                if not content.strip():
                    continue

                # Store row data cleanly in metadata dict
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
            print(f"❌ Error reading CSV file {file_path}: {e}")

    print(f"✅ Successfully loaded {len(documents)} clean documents from {len(csv_files)} CSV files.")
    return documents