-- Initiale vulling bytes
--
-- Wie : Mark
-- Datum : 23-11-2021
-- Waarom : Initiele versie


CREATE TABLE boefje_meta (
                             id UUID NOT NULL,
                             module_path VARCHAR NOT NULL,
                             module_version VARCHAR,
                             organization VARCHAR NOT NULL,
                             arguments JSON NOT NULL,
                             dispatches JSON,
                             started_at TIMESTAMP WITH TIME ZONE,
                             ended_at TIMESTAMP WITH TIME ZONE,
                             PRIMARY KEY (id),
                             UNIQUE (id)
);

Alter table boefje_meta owner to bytes_dba;

grant all on boefje_meta to bytes;

CREATE TABLE normalizer_meta (
                                 id UUID NOT NULL,
                                 module_path VARCHAR NOT NULL,
                                 module_version VARCHAR,
                                 started_at TIMESTAMP WITH TIME ZONE,
                                 ended_at TIMESTAMP WITH TIME ZONE,
                                 boefje_meta_id UUID NOT NULL,
                                 PRIMARY KEY (id),
                                 FOREIGN KEY(boefje_meta_id) REFERENCES boefje_meta (id),
                                 UNIQUE (id)
);

Alter table normalizer_meta owner to bytes_dba;

grant all on normalizer_meta to bytes;


CREATE TABLE output_ooi (
                            ooi_id VARCHAR NOT NULL,
                            normalizer_meta_id UUID NOT NULL,
                            PRIMARY KEY (ooi_id, normalizer_meta_id),
                            FOREIGN KEY(normalizer_meta_id) REFERENCES normalizer_meta (id)
);

Alter table output_ooi owner to bytes_dba;

grant all on output_ooi to bytes;

