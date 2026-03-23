/** Municipality geographic and demographic data */
export interface Municipality {
  id: string;
  mun_code: string;
  mun_name: string;
  province: string;
  district: string;
  latitude: number;
  longitude: number;
  population: number;
  youth_population: number;
}

/** Unemployment statistics per municipality per quarter */
export interface UnemploymentData {
  id: string;
  mun_code: string;
  year: number;
  quarter: number;
  unemployment_rate: number;
  youth_unemployment_rate: number;
  /** Not in Employment, Education or Training */
  neet_rate: number;
  absorption_rate: number;
}

/** Municipal financial data per financial year */
export interface MunicipalFinance {
  id: string;
  mun_code: string;
  financial_year: number;
  total_revenue: number;
  total_expenditure: number;
  capital_expenditure: number;
  operating_expenditure: number;
  service_delivery_spend: number;
  audit_outcome: string;
}

/** Skills gap data by province, sector, and occupation */
export interface SkillsGap {
  id: string;
  province: string;
  sector: string;
  occupation: string;
  demand_count: number;
  supply_count: number;
  gap: number;
  is_scarce: boolean;
  qualification_required: string;
}

/** Principal Component Analysis results per municipality */
export interface PCAResult {
  id: string;
  mun_code: string;
  pc1: number;
  pc2: number;
  pc3: number;
  cluster: number;
  profile_label: string;
  feature_loadings: Record<string, number>;
}

/** Municipality profile classification from SVM model */
export interface MunicipalProfile {
  id: string;
  mun_code: string;
  year: number;
  /** Profile category 1-4 */
  profile: number;
  welfare_measure: number;
  efficiency_measure: number;
  opportunity_measure: number;
  service_delivery_score: number;
}

/** Youth employment prediction from ML model */
export interface YouthPrediction {
  employment_probability: number;
  top_skills: string[];
  recommended_training: TrainingProgram[];
  /** Percentage of similar profiles that found employment */
  similar_profiles_outcome: number;
}

/** Training program information */
export interface TrainingProgram {
  id: string;
  name: string;
  provider: string;
  province: string;
  district: string;
  duration_months: number;
  cost: number;
  is_free: boolean;
  sector: string;
  qualification: string;
  /** Percentage of graduates employed within 6 months */
  employment_rate: number;
  url: string;
}

/** Employment, learnership, and training opportunities */
export interface Opportunity {
  id: string;
  title: string;
  type: 'learnership' | 'internship' | 'job' | 'bursary' | 'training';
  provider: string;
  province: string;
  district: string;
  sector: string;
  requirements: string;
  stipend: number | null;
  deadline: string;
  url: string;
  /** Source portal: SAYouth, SETA, YES4Youth, etc. */
  source: string;
  created_at: string;
}

/** Chat conversation message */
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

/** Chat session for analytics */
export interface ChatSession {
  id: string;
  started_at: string;
  ended_at: string | null;
  message_count: number;
  topics: string[];
}

/** Data ingestion log entry */
export interface DataIngestionLog {
  id: string;
  source: string;
  started_at: string;
  completed_at: string | null;
  status: 'running' | 'completed' | 'failed';
  records_processed: number;
  error_message: string | null;
}
