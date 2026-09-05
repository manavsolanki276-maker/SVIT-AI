"""
tests/test_module_scoped_rag.py
Automated Verification Suite for:
1. Universal Multi-Format Document Ingestion (.pdf, .docx, .xlsx, .csv, .txt)
2. SHA-256 Duplicate Content Prevention (409 Conflict)
3. Strict 8-Step Verification Pipeline
4. Page-Specific RAG Isolation across Module Namespaces (Zero Cross-Module Contamination)
5. Document Lifecycle (Re-indexing & Vector Cleanup on Deletion)
6. Legacy Module Graceful Redirection (Zero 404s for retired Library/Sports routes)
"""
import io
import os
import sys
import unittest
import json
import uuid

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.database.admin_seed import seed_admin_accounts
from app.database.admin_crud_service import initialize_datasets_if_needed, AdminCRUDService
from app.ai.rag_pipeline import get_rag_pipeline
from app.ai.retriever import retrieve_by_module
from app.ai.vector_store import build_or_load_vector_store
from app.ai.document_processor import (
    extract_document_text,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_tabular,
    extract_text_from_txt,
    calculate_file_hash,
    process_and_index_document,
    remove_document_from_rag
)


def create_sample_pdf(text: str) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 750, text)
    c.save()
    return buf.getvalue()


def create_sample_docx(text: str) -> bytes:
    import docx
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def create_sample_xlsx(rows: list) -> bytes:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestModuleScopedRAG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['FAST_EMBEDDINGS'] = '1'
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            db.create_all()
            seed_admin_accounts(cls.app)
            initialize_datasets_if_needed()
            cls.pipeline = get_rag_pipeline(force_rebuild=False)
            cls.vector_store = cls.pipeline.vector_store

    def login_as_super_admin(self):
        res = self.client.post('/admin/login', json={
            "identifier": "superadmin",
            "password": "Admin@123"
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 200)
        return res

    # -------------------------------------------------------------------------
    # 1. MULTI-FORMAT TEXT EXTRACTION
    # -------------------------------------------------------------------------
    def test_01_extract_pdf(self):
        """Tests text extraction from PDF files."""
        pdf_bytes = create_sample_pdf("SVIT Vasad official test: TOKEN-PDF-TEST-12345.")
        tmp_path = os.path.join(self.app.root_path, "static", "uploads", "documents", "test_sample.pdf")
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        with open(tmp_path, "wb") as f:
            f.write(pdf_bytes)

        try:
            ok, msg, pages, meta = extract_document_text(tmp_path, "pdf")
            self.assertTrue(ok)
            self.assertIn("TOKEN-PDF-TEST-12345", pages[0]["text"])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_02_extract_docx(self):
        """Tests text extraction from DOCX files."""
        docx_bytes = create_sample_docx("SVIT Vasad official test: TOKEN-DOCX-TEST-67890.")
        tmp_path = os.path.join(self.app.root_path, "static", "uploads", "documents", "test_sample.docx")
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        with open(tmp_path, "wb") as f:
            f.write(docx_bytes)

        try:
            ok, msg, pages, meta = extract_document_text(tmp_path, "docx")
            self.assertTrue(ok)
            self.assertIn("TOKEN-DOCX-TEST-67890", pages[0]["text"])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_03_extract_xlsx_and_csv(self):
        """Tests tabular extraction from XLSX and CSV files."""
        rows = [["ID", "Route", "Token"], ["R-1", "Vadodara to SVIT", "TOKEN-TABULAR-ROUTEX"]]
        xlsx_bytes = create_sample_xlsx(rows)
        tmp_xlsx = os.path.join(self.app.root_path, "static", "uploads", "documents", "test_sample.xlsx")
        os.makedirs(os.path.dirname(tmp_xlsx), exist_ok=True)
        with open(tmp_xlsx, "wb") as f:
            f.write(xlsx_bytes)

        csv_content = "ID,Route,Token\nR-2,Anand to SVIT,TOKEN-CSV-ROUTEY\n"
        tmp_csv = os.path.join(self.app.root_path, "static", "uploads", "documents", "test_sample.csv")
        with open(tmp_csv, "w", encoding="utf-8") as f:
            f.write(csv_content)

        try:
            ok_x, _, pages_x, _ = extract_document_text(tmp_xlsx, "xlsx")
            self.assertTrue(ok_x)
            self.assertIn("TOKEN-TABULAR-ROUTEX", pages_x[0]["text"])

            ok_c, _, pages_c, _ = extract_document_text(tmp_csv, "csv")
            self.assertTrue(ok_c)
            self.assertIn("TOKEN-CSV-ROUTEY", pages_c[0]["text"])
        finally:
            for p in [tmp_xlsx, tmp_csv]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass

    def test_04_extract_txt(self):
        """Tests plain text extraction."""
        tmp_txt = os.path.join(self.app.root_path, "static", "uploads", "documents", "test_sample.txt")
        os.makedirs(os.path.dirname(tmp_txt), exist_ok=True)
        with open(tmp_txt, "w", encoding="utf-8") as f:
            f.write("Sardar Vallabhbhai Patel Institute of Technology Vasad TOKEN-TXT-999.")

        try:
            ok, msg, pages, meta = extract_document_text(tmp_txt, "txt")
            self.assertTrue(ok)
            self.assertIn("TOKEN-TXT-999", pages[0]["text"])
        finally:
            if os.path.exists(tmp_txt):
                os.remove(tmp_txt)

    # -------------------------------------------------------------------------
    # 2. PAGE-SPECIFIC RAG ISOLATION
    # -------------------------------------------------------------------------
    def test_05_strict_namespace_isolation(self):
        """
        Ingests distinct unique tokens into 'admission', 'bus', and 'syllabus' namespaces.
        Verifies that querying a specific namespace NEVER leaks chunks from any other namespace.
        """
        token_adm = f"TOKEN-ADM-{uuid.uuid4().hex[:8]}"
        token_bus = f"TOKEN-BUS-{uuid.uuid4().hex[:8]}"
        token_syl = f"TOKEN-SYL-{uuid.uuid4().hex[:8]}"

        pdf_adm = create_sample_pdf(f"Official Admission Criteria at SVIT: {token_adm} only for admission candidates.")
        pdf_bus = create_sample_pdf(f"Official Bus Transport Schedule at SVIT: {token_bus} only for bus commuters.")
        pdf_syl = create_sample_pdf(f"Official GTU Computer Engineering Syllabus: {token_syl} only for academics.")

        doc_dir = os.path.join(self.app.root_path, "static", "uploads", "documents")
        os.makedirs(doc_dir, exist_ok=True)

        path_adm = os.path.join(doc_dir, "iso_adm.pdf")
        path_bus = os.path.join(doc_dir, "iso_bus.pdf")
        path_syl = os.path.join(doc_dir, "iso_syl.pdf")

        with open(path_adm, "wb") as f: f.write(pdf_adm)
        with open(path_bus, "wb") as f: f.write(pdf_bus)
        with open(path_syl, "wb") as f: f.write(pdf_syl)

        meta_adm = {"document_id": "DOC-ISO-ADM", "file_name": "iso_adm.pdf", "module": "admission", "rag_namespace": "admission"}
        meta_bus = {"document_id": "DOC-ISO-BUS", "file_name": "iso_bus.pdf", "module": "bus", "rag_namespace": "bus"}
        meta_syl = {"document_id": "DOC-ISO-SYL", "file_name": "iso_syl.pdf", "module": "syllabus", "rag_namespace": "syllabus"}

        try:
            ok_a, _, _, _ = process_and_index_document(path_adm, meta_adm, self.vector_store)
            ok_b, _, _, _ = process_and_index_document(path_bus, meta_bus, self.vector_store)
            ok_s, _, _, _ = process_and_index_document(path_syl, meta_syl, self.vector_store)

            self.assertTrue(ok_a)
            self.assertTrue(ok_b)
            self.assertTrue(ok_s)

            # Query admission namespace: must find token_adm, must NOT find token_bus or token_syl
            adm_res = retrieve_by_module(self.vector_store, token_adm, module="admission", k=5)
            adm_texts = " ".join([d.page_content for d, _ in adm_res])
            self.assertIn(token_adm, adm_texts)

            adm_leak_check = retrieve_by_module(self.vector_store, token_bus, module="admission", k=5)
            adm_leak_texts = " ".join([d.page_content for d, _ in adm_leak_check])
            self.assertNotIn(token_bus, adm_leak_texts, "Cross-contamination! Admission retrieved Bus chunk.")

            # Query bus namespace: must find token_bus, must NOT find token_adm or token_syl
            bus_res = retrieve_by_module(self.vector_store, token_bus, module="bus", k=5)
            bus_texts = " ".join([d.page_content for d, _ in bus_res])
            self.assertIn(token_bus, bus_texts)

            bus_leak_check = retrieve_by_module(self.vector_store, token_syl, module="bus", k=5)
            bus_leak_texts = " ".join([d.page_content for d, _ in bus_leak_check])
            self.assertNotIn(token_syl, bus_leak_texts, "Cross-contamination! Bus retrieved Syllabus chunk.")

            # Query syllabus namespace: must find token_syl, must NOT find token_adm or token_bus
            syl_res = retrieve_by_module(self.vector_store, token_syl, module="syllabus", k=5)
            syl_texts = " ".join([d.page_content for d, _ in syl_res])
            self.assertIn(token_syl, syl_texts)

            syl_leak_check = retrieve_by_module(self.vector_store, token_adm, module="syllabus", k=5)
            syl_leak_texts = " ".join([d.page_content for d, _ in syl_leak_check])
            self.assertNotIn(token_adm, syl_leak_texts, "Cross-contamination! Syllabus retrieved Admission chunk.")

        finally:
            remove_document_from_rag("DOC-ISO-ADM", self.vector_store)
            remove_document_from_rag("DOC-ISO-BUS", self.vector_store)
            remove_document_from_rag("DOC-ISO-SYL", self.vector_store)
            for p in [path_adm, path_bus, path_syl]:
                if os.path.exists(p):
                    os.remove(p)

    def test_05b_mandatory_phase16_cross_module_isolation(self):
        """
        PHASE 16 MANDATORY CROSS-MODULE RAG TEST
        Creates 8 isolated tokens across all 8 namespaces:
        Admission: TEST-ADM-9281
        Bus: TEST-BUS-5931
        Canteen: TEST-CAN-1234
        Notice: TEST-NOT-5678
        Event: TEST-EVT-9012
        SVIT Info: TEST-SVT-3456
        Syllabus: TEST-SYL-7890
        Faculty: TEST-FAC-2468

        Verifies each module retrieves its own token and NEVER retrieves another module's token.
        """
        token_map = {
            "admission": "TEST-ADM-9281",
            "bus": "TEST-BUS-5931",
            "canteen": "TEST-CAN-1234",
            "notices": "TEST-NOT-5678",
            "events": "TEST-EVT-9012",
            "svit_info": "TEST-SVT-3456",
            "syllabus": "TEST-SYL-7890",
            "faculty": "TEST-FAC-2468",
        }

        doc_dir = os.path.join(self.app.root_path, "static", "uploads", "documents")
        os.makedirs(doc_dir, exist_ok=True)
        created_paths = []
        created_doc_ids = []

        try:
            for mod, token in token_map.items():
                content = f"Official SVIT institutional document for module {mod}: verified isolated token {token}."
                pdf_bytes = create_sample_pdf(content)
                file_path = os.path.join(doc_dir, f"phase16_{mod}.pdf")
                with open(file_path, "wb") as f:
                    f.write(pdf_bytes)
                created_paths.append(file_path)

                doc_id = f"DOC-P16-{mod.upper()}"
                created_doc_ids.append(doc_id)
                meta = {
                    "document_id": doc_id,
                    "file_name": f"phase16_{mod}.pdf",
                    "module": mod,
                    "rag_namespace": mod
                }
                ok, msg, count, _ = process_and_index_document(file_path, meta, self.vector_store)
                self.assertTrue(ok, f"Failed to ingest for {mod}: {msg}")

            # Verify every module retrieves ITS OWN token
            for mod, expected_token in token_map.items():
                own_results = retrieve_by_module(self.vector_store, expected_token, module=mod, k=5)
                own_text = " ".join([d.page_content for d, _ in own_results])
                self.assertIn(expected_token, own_text, f"Module '{mod}' failed to retrieve its own token '{expected_token}'.")

                # Verify it NEVER retrieves any foreign token
                for foreign_mod, foreign_token in token_map.items():
                    if foreign_mod == mod:
                        continue
                    leak_results = retrieve_by_module(self.vector_store, foreign_token, module=mod, k=5)
                    leak_text = " ".join([d.page_content for d, _ in leak_results])
                    self.assertNotIn(foreign_token, leak_text, f"LEAKAGE DETECTED! Module '{mod}' retrieved foreign token '{foreign_token}' from '{foreign_mod}'.")

        finally:
            for doc_id in created_doc_ids:
                remove_document_from_rag(doc_id, self.vector_store)
            for p in created_paths:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass

    # -------------------------------------------------------------------------
    # 3. SHA-256 DUPLICATE DETECTION API TEST
    # -------------------------------------------------------------------------
    def test_06_sha256_duplicate_detection_via_api(self):
        """Tests that uploading an identical file twice triggers 409 Conflict."""
        self.login_as_super_admin()

        pdf_bytes = create_sample_pdf("SVIT Vasad Unique Duplicate Check Content: HASH-DUP-TEST-XYZ")
        
        # 1st Upload
        data = {
            'module': 'svit_info',
            'title': 'Original Unique Upload',
            'file': (io.BytesIO(pdf_bytes), 'dup_test_1.pdf')
        }
        res1 = self.client.post('/admin/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertIn(res1.status_code, [200, 201])
        doc_info = res1.get_json()["document"]
        doc_id = doc_info["document_id"]

        # 2nd Upload with exact same content
        data2 = {
            'module': 'svit_info',
            'title': 'Duplicate Content Upload',
            'file': (io.BytesIO(pdf_bytes), 'dup_test_2.pdf')
        }
        res2 = self.client.post('/admin/api/documents/upload', data=data2, content_type='multipart/form-data')
        self.assertEqual(res2.status_code, 409, "Server did not reject duplicate document with 409 Conflict.")
        json_res = res2.get_json()
        self.assertEqual(json_res.get("status"), "error")
        self.assertEqual(json_res.get("error"), "DuplicateDocument")
        self.assertIn("identical content", json_res.get("message", "").lower())

        # Cleanup
        del_res = self.client.delete(f'/admin/api/documents/{doc_id}')
        self.assertEqual(del_res.status_code, 200)

    # -------------------------------------------------------------------------
    # 4. DOCUMENT RE-INDEXING & DELETION VECTOR PURGE
    # -------------------------------------------------------------------------
    def test_07_document_deletion_vector_purge(self):
        """Tests that deleting a document purges all vectors so subsequent queries return nothing."""
        token_del = f"TOKEN-PURGE-{uuid.uuid4().hex[:8]}"
        pdf_bytes = create_sample_pdf(f"Purge verification text: {token_del} in SVIT system.")
        doc_path = os.path.join(self.app.root_path, "static", "uploads", "documents", "purge_test.pdf")
        os.makedirs(os.path.dirname(doc_path), exist_ok=True)
        with open(doc_path, "wb") as f:
            f.write(pdf_bytes)

        doc_id = f"DOC-PURGE-{uuid.uuid4().hex[:6]}"
        meta = {"document_id": doc_id, "file_name": "purge_test.pdf", "module": "notices", "rag_namespace": "notices"}

        try:
            ok, msg, count, _ = process_and_index_document(doc_path, meta, self.vector_store)
            self.assertTrue(ok)
            self.assertGreater(count, 0)

            # Confirm indexed
            matches = retrieve_by_module(self.vector_store, token_del, module="notices")
            self.assertTrue(any(token_del in d.page_content for d, _ in matches))

            # Purge
            remove_document_from_rag(doc_id, self.vector_store)

            # Confirm purged
            matches_after = retrieve_by_module(self.vector_store, token_del, module="notices")
            self.assertFalse(any(token_del in d.page_content for d, _ in matches_after))

        finally:
            if os.path.exists(doc_path):
                os.remove(doc_path)

    # -------------------------------------------------------------------------
    # 5. LEGACY MODULE GRACEFUL REDIRECT (NO 404s)
    # -------------------------------------------------------------------------
    def test_08_retired_modules_graceful_redirect(self):
        """Tests that legacy library and sports URLs redirect cleanly without 404 errors."""
        self.login_as_super_admin()

        retired_urls = [
            '/admin/library',
            '/admin/library_books',
            '/admin/library_members',
            '/admin/issue_return',
            '/admin/sports',
            '/admin/sports_events',
            '/admin/grounds'
        ]

        for url in retired_urls:
            res = self.client.get(url, follow_redirects=False)
            self.assertIn(res.status_code, [302, 301], f"Route {url} did not redirect gracefully.")
            self.assertIn('/admin/dashboard', res.headers.get('Location', ''))


if __name__ == '__main__':
    unittest.main()
