-- Wie : Herman (Jesse)
-- Datum : 14-01-2022
-- Waarom : versie bump

ALTER TABLE boefje_meta RENAME module_path TO boefje_name;
ALTER TABLE boefje_meta RENAME module_version TO boefje_version;
ALTER TABLE normalizer_meta RENAME module_path TO normalizer_name;
ALTER TABLE normalizer_meta RENAME module_version TO normalizer_version;