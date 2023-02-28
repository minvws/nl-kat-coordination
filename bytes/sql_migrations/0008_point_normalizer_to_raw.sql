ALTER TABLE normalizer_meta ADD COLUMN raw_file_id UUID;
ALTER TABLE normalizer_meta ADD CONSTRAINT normalizer_meta_raw_file_id_fkey FOREIGN KEY(raw_file_id) REFERENCES raw_file (id) ON DELETE CASCADE;
