-- Run as the managed database owner with passwords supplied by the secret manager.
-- This file deliberately creates no passwords and is safe to version.
DO $$ BEGIN CREATE ROLE nextleap_migration NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE nextleap_api NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE nextleap_ingestion NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE nextleap_audit_reader NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT USAGE ON SCHEMA public TO nextleap_api, nextleap_ingestion, nextleap_audit_reader;
GRANT SELECT ON dataset_versions, restaurants, budget_profiles TO nextleap_api;
GRANT INSERT ON recommendation_audits TO nextleap_api;
GRANT SELECT, INSERT, UPDATE ON dataset_versions, restaurants, budget_profiles TO nextleap_ingestion;
GRANT SELECT ON recommendation_audits TO nextleap_audit_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE nextleap_migration IN SCHEMA public GRANT SELECT ON TABLES TO nextleap_api;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
