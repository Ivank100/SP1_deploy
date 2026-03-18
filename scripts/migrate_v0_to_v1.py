# backend/migrate_v0_to_v1.py
"""
Migration script to convert v0 data (document_chunks) to v1 schema (lectures + chunks).

This script:
1. Reads all unique doc_id values from document_chunks
2. Creates a lecture record for each doc_id
3. Migrates chunks to the new chunks table with page_number=0 (unknown)
4. Optionally drops the old document_chunks table

Run this once after upgrading to v1 schema.
"""
import sys
from backend.db.postgres import get_conn, init_schema

def migrate():
    """Migrate data from document_chunks to lectures + chunks."""
    init_schema()
    
    with get_conn() as conn, conn.cursor() as cur:
        # Check if document_chunks table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'document_chunks'
            );
        """)
        if not cur.fetchone()[0]:
            print("[INFO] document_chunks table doesn't exist. Nothing to migrate.")
            return
        
        # Get all unique doc_ids
        cur.execute("SELECT DISTINCT doc_id FROM document_chunks")
        doc_ids = [row[0] for row in cur.fetchall()]
        
        if not doc_ids:
            print("[INFO] No data in document_chunks. Nothing to migrate.")
            return
        
        print(f"[INFO] Found {len(doc_ids)} document(s) to migrate")
        
        migrated_count = 0
        for doc_id in doc_ids:
            # Create lecture record
            cur.execute("""
                INSERT INTO lectures (original_name, file_path, page_count, status)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (doc_id, f"migrated/{doc_id}", 0, "completed"))
            lecture_id = cur.fetchone()[0]
            
            # Get chunks for this doc_id
            cur.execute("""
                SELECT chunk_index, content, embedding
                FROM document_chunks
                WHERE doc_id = %s
                ORDER BY chunk_index
            """, (doc_id,))
            chunks = cur.fetchall()
            
            # Insert into new chunks table
            for chunk_index, content, embedding in chunks:
                cur.execute("""
                    INSERT INTO chunks (lecture_id, page_number, chunk_index, text, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                """, (lecture_id, 0, chunk_index, content, embedding))
            
            migrated_count += len(chunks)
            print(f"[INFO] Migrated doc_id={doc_id} -> lecture_id={lecture_id} ({len(chunks)} chunks)")
        
        conn.commit()
        print(f"[SUCCESS] Migration complete: {len(doc_ids)} lectures, {migrated_count} total chunks")
        
        # Ask if user wants to drop old table
        response = input("\nDrop old document_chunks table? (y/N): ").strip().lower()
        if response == 'y':
            cur.execute("DROP TABLE IF EXISTS document_chunks")
            conn.commit()
            print("[INFO] Dropped document_chunks table")
        else:
            print("[INFO] Kept document_chunks table (you can drop it manually later)")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)
