export interface KbDocument {
  id: number;
  original_filename: string;
  created_at: string;
}

export interface IngestJob {
  id: number;
  document_id: number;
  filename: string;
  status: string;
  vector_ok: boolean;
  keyword_ok: boolean;
  metadata_ok: boolean;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface UploadKbResult {
  document: KbDocument;
  job: IngestJob;
}
