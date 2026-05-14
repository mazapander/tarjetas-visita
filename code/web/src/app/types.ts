export interface ContactMethod {
  method_type: string;
  raw_value: string;
  normalized_value: string;
  label?: string | null;
  is_primary: boolean;
}

export interface ContactSummary {
  contact_id: number;
  document_id: string;
  source_file?: string | null;
  contact_index: number;
  full_name?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  company?: string | null;
  job_title?: string | null;
  department?: string | null;
  website?: string | null;
  linkedin?: string | null;
  address?: string | null;
  city?: string | null;
  province?: string | null;
  postal_code?: string | null;
  country?: string | null;
  notes?: string | null;
  contact_methods: ContactMethod[];
  extraction_method?: string | null;
  confidence?: number | null;
  warnings: string[];
}

export interface ContactsResponse {
  total_count: number;
  items: ContactSummary[];
}

export interface DashboardSummary {
  total_documents: number;
  total_contacts: number;
  low_confidence_contacts: number;
  contacts_with_warnings: number;
  contacts_without_email: number;
  contacts_without_phone: number;
  possible_duplicates: number;
  low_confidence_threshold: number;
}

export interface ContactDetailResponse {
  contact: ContactSummary;
  document: {
    document_id: string;
    source_file: string;
    source_path: string;
    uploaded_at: string | null;
    document_status: string;
    image_url: string;
  };
  ocr: {
    provider: string | null;
    model: string | null;
    markdown: string;
    average_confidence: number | null;
    pages_processed: number | null;
    processed_at: string | null;
  };
}

export interface ContactUpdatePayload {
  full_name: string | null;
  first_name: string | null;
  last_name: string | null;
  company: string | null;
  job_title: string | null;
  department: string | null;
  website: string | null;
  linkedin: string | null;
  address: string | null;
  city: string | null;
  province: string | null;
  postal_code: string | null;
  country: string | null;
  notes: string | null;
  contact_methods: ContactMethod[];
  confidence: number | null;
  warnings: string[];
  extraction_version?: string;
}

export interface ProcessResult {
  mode: string;
  total_discovered: number;
  selected_for_processing: number;
  ocr_processed: number;
  reused_saved_ocr: number;
  contacts_extracted: number;
  total_contacts_persisted: number;
  missing_ocr_documents: string[];
}

export interface ContactFormValues {
  full_name: string;
  first_name: string;
  last_name: string;
  company: string;
  job_title: string;
  department: string;
  email: string;
  mobile: string;
  phone: string;
  website: string;
  linkedin: string;
  address: string;
  city: string;
  province: string;
  postal_code: string;
  country: string;
  confidence: string;
  notes: string;
  warnings: string;
}
