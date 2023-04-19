-- Wie : Mark
-- Datum : 16-12-2021
-- Waarom : Versie 0.2.0

DROP TABLE output_ooi;

ALTER TABLE normalizer_meta
DROP CONSTRAINT normalizer_meta_boefje_meta_id_fkey;

ALTER TABLE normalizer_meta
    ADD CONSTRAINT normalizer_meta_boefje_meta_id_fkey
        FOREIGN KEY(boefje_meta_id)
            REFERENCES boefje_meta (id)
            ON DELETE CASCADE;

DELETE FROM boefje_meta;

ALTER TABLE boefje_meta
    ADD COLUMN input_ooi
        VARCHAR NOT NULL;
