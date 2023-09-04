CREATE TABLE signing_provider (
    id SERIAL NOT NULL,
    url VARCHAR(256) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (url)
);

ALTER TABLE raw_file ADD COLUMN signing_provider_id INTEGER;

CREATE INDEX ix_raw_file_signing_provider_id ON raw_file (signing_provider_id);
ALTER TABLE raw_file ADD FOREIGN KEY(signing_provider_id) REFERENCES signing_provider (id) ON DELETE CASCADE;
