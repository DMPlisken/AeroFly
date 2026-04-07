-- AeroFly PostgreSQL initialization
-- Creates schemas for each service module

CREATE SCHEMA IF NOT EXISTS gateway;
CREATE SCHEMA IF NOT EXISTS data_ingestion;
CREATE SCHEMA IF NOT EXISTS search;

-- Grant usage
GRANT ALL ON SCHEMA gateway TO aerofly;
GRANT ALL ON SCHEMA data_ingestion TO aerofly;
GRANT ALL ON SCHEMA search TO aerofly;
