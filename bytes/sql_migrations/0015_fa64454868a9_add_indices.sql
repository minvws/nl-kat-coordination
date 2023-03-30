CREATE INDEX CONCURRENTLY ix_boefje_meta_organization_boefje_id ON boefje_meta (organization, boefje_id);
CREATE INDEX CONCURRENTLY ix_normalizer_meta_raw_file_id ON normalizer_meta (raw_file_id);
CREATE INDEX CONCURRENTLY ix_raw_file_boefje_meta_id ON raw_file (boefje_meta_id);
