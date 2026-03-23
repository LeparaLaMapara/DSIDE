-- DSIDE Platform: Initial Database Schema
-- South African Youth Unemployment & Municipal Service Delivery Intelligence

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- ============================================================
-- MUNICIPALITIES
-- ============================================================
CREATE TABLE municipalities (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mun_code VARCHAR(10) UNIQUE NOT NULL,
  mun_name VARCHAR(255) NOT NULL,
  province VARCHAR(100) NOT NULL,
  district VARCHAR(255) NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  population INTEGER NOT NULL DEFAULT 0,
  youth_population INTEGER NOT NULL DEFAULT 0,
  geom GEOMETRY(Point, 4326),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_municipalities_mun_code ON municipalities(mun_code);
CREATE INDEX idx_municipalities_province ON municipalities(province);
CREATE INDEX idx_municipalities_district ON municipalities(district);
CREATE INDEX idx_municipalities_geom ON municipalities USING GIST(geom);

-- ============================================================
-- UNEMPLOYMENT DATA
-- ============================================================
CREATE TABLE unemployment_data (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mun_code VARCHAR(10) NOT NULL REFERENCES municipalities(mun_code) ON DELETE CASCADE,
  year INTEGER NOT NULL,
  quarter INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
  unemployment_rate DOUBLE PRECISION,
  youth_unemployment_rate DOUBLE PRECISION,
  neet_rate DOUBLE PRECISION,
  absorption_rate DOUBLE PRECISION,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(mun_code, year, quarter)
);

CREATE INDEX idx_unemployment_mun_code ON unemployment_data(mun_code);
CREATE INDEX idx_unemployment_year_quarter ON unemployment_data(year, quarter);
CREATE INDEX idx_unemployment_youth_rate ON unemployment_data(youth_unemployment_rate);

-- ============================================================
-- MUNICIPAL FINANCES
-- ============================================================
CREATE TABLE municipal_finances (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mun_code VARCHAR(10) NOT NULL REFERENCES municipalities(mun_code) ON DELETE CASCADE,
  financial_year INTEGER NOT NULL,
  total_revenue BIGINT NOT NULL DEFAULT 0,
  total_expenditure BIGINT NOT NULL DEFAULT 0,
  capital_expenditure BIGINT NOT NULL DEFAULT 0,
  operating_expenditure BIGINT NOT NULL DEFAULT 0,
  service_delivery_spend BIGINT NOT NULL DEFAULT 0,
  audit_outcome VARCHAR(100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(mun_code, financial_year)
);

CREATE INDEX idx_finances_mun_code ON municipal_finances(mun_code);
CREATE INDEX idx_finances_year ON municipal_finances(financial_year);
CREATE INDEX idx_finances_audit ON municipal_finances(audit_outcome);

-- ============================================================
-- SKILLS GAPS
-- ============================================================
CREATE TABLE skills_gaps (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  province VARCHAR(100) NOT NULL,
  sector VARCHAR(255) NOT NULL,
  occupation VARCHAR(255) NOT NULL,
  demand_count INTEGER NOT NULL DEFAULT 0,
  supply_count INTEGER NOT NULL DEFAULT 0,
  gap INTEGER NOT NULL DEFAULT 0,
  is_scarce BOOLEAN NOT NULL DEFAULT FALSE,
  qualification_required VARCHAR(255),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_skills_gaps_province ON skills_gaps(province);
CREATE INDEX idx_skills_gaps_sector ON skills_gaps(sector);
CREATE INDEX idx_skills_gaps_scarce ON skills_gaps(is_scarce);
CREATE INDEX idx_skills_gaps_gap ON skills_gaps(gap DESC);

-- ============================================================
-- PCA RESULTS
-- ============================================================
CREATE TABLE pca_results (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mun_code VARCHAR(10) NOT NULL REFERENCES municipalities(mun_code) ON DELETE CASCADE,
  pc1 DOUBLE PRECISION NOT NULL,
  pc2 DOUBLE PRECISION NOT NULL,
  pc3 DOUBLE PRECISION NOT NULL,
  cluster INTEGER NOT NULL,
  profile_label VARCHAR(100),
  feature_loadings JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(mun_code)
);

CREATE INDEX idx_pca_mun_code ON pca_results(mun_code);
CREATE INDEX idx_pca_cluster ON pca_results(cluster);
CREATE INDEX idx_pca_loadings ON pca_results USING GIN(feature_loadings);

-- ============================================================
-- MUNICIPAL PROFILES (SVM Classification)
-- ============================================================
CREATE TABLE municipal_profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mun_code VARCHAR(10) NOT NULL REFERENCES municipalities(mun_code) ON DELETE CASCADE,
  year INTEGER NOT NULL,
  profile INTEGER NOT NULL CHECK (profile BETWEEN 1 AND 4),
  welfare_measure DOUBLE PRECISION NOT NULL DEFAULT 0,
  efficiency_measure DOUBLE PRECISION NOT NULL DEFAULT 0,
  opportunity_measure DOUBLE PRECISION NOT NULL DEFAULT 0,
  service_delivery_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(mun_code, year)
);

CREATE INDEX idx_profiles_mun_code ON municipal_profiles(mun_code);
CREATE INDEX idx_profiles_year ON municipal_profiles(year);
CREATE INDEX idx_profiles_profile ON municipal_profiles(profile);

-- ============================================================
-- TRAINING PROGRAMS
-- ============================================================
CREATE TABLE training_programs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(500) NOT NULL,
  provider VARCHAR(255) NOT NULL,
  province VARCHAR(100) NOT NULL,
  district VARCHAR(255),
  duration_months INTEGER,
  cost INTEGER NOT NULL DEFAULT 0,
  is_free BOOLEAN NOT NULL DEFAULT FALSE,
  sector VARCHAR(255),
  qualification VARCHAR(255),
  employment_rate DOUBLE PRECISION,
  url VARCHAR(1000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_training_province ON training_programs(province);
CREATE INDEX idx_training_sector ON training_programs(sector);
CREATE INDEX idx_training_free ON training_programs(is_free);
CREATE INDEX idx_training_employment ON training_programs(employment_rate DESC NULLS LAST);

-- ============================================================
-- OPPORTUNITIES
-- ============================================================
CREATE TABLE opportunities (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title VARCHAR(500) NOT NULL,
  type VARCHAR(50) NOT NULL CHECK (type IN ('learnership', 'internship', 'job', 'bursary', 'training')),
  provider VARCHAR(255) NOT NULL,
  province VARCHAR(100) NOT NULL,
  district VARCHAR(255),
  sector VARCHAR(255),
  requirements TEXT,
  stipend INTEGER,
  deadline DATE,
  url VARCHAR(1000),
  source VARCHAR(100) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_opportunities_type ON opportunities(type);
CREATE INDEX idx_opportunities_province ON opportunities(province);
CREATE INDEX idx_opportunities_sector ON opportunities(sector);
CREATE INDEX idx_opportunities_source ON opportunities(source);
CREATE INDEX idx_opportunities_deadline ON opportunities(deadline);
CREATE INDEX idx_opportunities_active ON opportunities(is_active) WHERE is_active = TRUE;

-- ============================================================
-- CHAT SESSIONS (Anonymous Analytics)
-- ============================================================
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  message_count INTEGER NOT NULL DEFAULT 0,
  topics TEXT[] DEFAULT '{}',
  user_province VARCHAR(100),
  user_age_group VARCHAR(20)
);

CREATE INDEX idx_chat_sessions_started ON chat_sessions(started_at);

-- ============================================================
-- DATA INGESTION LOG
-- ============================================================
CREATE TABLE data_ingestion_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source VARCHAR(255) NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  status VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
  records_processed INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_ingestion_source ON data_ingestion_log(source);
CREATE INDEX idx_ingestion_status ON data_ingestion_log(status);
CREATE INDEX idx_ingestion_started ON data_ingestion_log(started_at DESC);

-- ============================================================
-- AUTO-UPDATE TIMESTAMPS
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_municipalities_updated_at BEFORE UPDATE ON municipalities FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_unemployment_updated_at BEFORE UPDATE ON unemployment_data FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_finances_updated_at BEFORE UPDATE ON municipal_finances FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_skills_gaps_updated_at BEFORE UPDATE ON skills_gaps FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_pca_results_updated_at BEFORE UPDATE ON pca_results FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_profiles_updated_at BEFORE UPDATE ON municipal_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_training_updated_at BEFORE UPDATE ON training_programs FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_opportunities_updated_at BEFORE UPDATE ON opportunities FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE municipalities ENABLE ROW LEVEL SECURITY;
ALTER TABLE unemployment_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE municipal_finances ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills_gaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE pca_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE municipal_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_ingestion_log ENABLE ROW LEVEL SECURITY;

-- Public read access (anon and authenticated)
CREATE POLICY "Public read municipalities" ON municipalities FOR SELECT USING (true);
CREATE POLICY "Public read unemployment" ON unemployment_data FOR SELECT USING (true);
CREATE POLICY "Public read finances" ON municipal_finances FOR SELECT USING (true);
CREATE POLICY "Public read skills gaps" ON skills_gaps FOR SELECT USING (true);
CREATE POLICY "Public read PCA results" ON pca_results FOR SELECT USING (true);
CREATE POLICY "Public read profiles" ON municipal_profiles FOR SELECT USING (true);
CREATE POLICY "Public read training" ON training_programs FOR SELECT USING (true);
CREATE POLICY "Public read opportunities" ON opportunities FOR SELECT USING (true);

-- Chat sessions: anyone can insert (anonymous analytics), only service role can read
CREATE POLICY "Anyone can create chat sessions" ON chat_sessions FOR INSERT WITH CHECK (true);
CREATE POLICY "Service role reads chat sessions" ON chat_sessions FOR SELECT USING (auth.role() = 'service_role');

-- Ingestion log: only service role
CREATE POLICY "Service role manages ingestion log" ON data_ingestion_log FOR ALL USING (auth.role() = 'service_role');

-- Write access restricted to service role (applied via service role key bypassing RLS)
-- The service role key automatically bypasses RLS, so no explicit write policies needed
-- for data tables. The anon key cannot write due to absence of INSERT/UPDATE/DELETE policies.
