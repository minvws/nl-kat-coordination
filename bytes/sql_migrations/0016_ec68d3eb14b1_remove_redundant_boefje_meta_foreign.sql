INSERT INTO raw_file (id, boefje_meta_id) SELECT DISTINCT boefje_meta_id AS id, boefje_meta_id AS boefje_meta_id FROM normalizer_meta WHERE raw_file_id IS NULL;
UPDATE normalizer_meta SET raw_file_id = boefje_meta_id WHERE raw_file_id IS NULL;

ALTER TABLE normalizer_meta ALTER COLUMN raw_file_id SET NOT NULL;
ALTER TABLE normalizer_meta DROP CONSTRAINT normalizer_meta_boefje_meta_id_fkey;
ALTER TABLE normalizer_meta DROP COLUMN boefje_meta_id;