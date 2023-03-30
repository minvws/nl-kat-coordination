CREATE TABLE raw_file (
    id UUID NOT NULL,
    secure_hash VARCHAR,
    hash_retrieval_link VARCHAR,
    boefje_meta_id UUID NOT NULL,
    mime_types VARCHAR[],
    PRIMARY KEY (id),
    FOREIGN KEY(boefje_meta_id) REFERENCES boefje_meta (id) ON DELETE CASCADE
);

ALTER TABLE boefje_meta DROP COLUMN hash_retrieval_link;
ALTER TABLE boefje_meta DROP COLUMN secure_hash;
