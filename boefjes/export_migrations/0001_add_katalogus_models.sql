
CREATE TABLE organisation (
    pk SERIAL NOT NULL,
    id VARCHAR(4) NOT NULL,
    name VARCHAR(32) NOT NULL,
    PRIMARY KEY (pk)
);

CREATE TABLE repository (
    pk SERIAL NOT NULL,
    id VARCHAR(32) NOT NULL,
    name VARCHAR(64) NOT NULL,
    base_url VARCHAR(128) NOT NULL,
    PRIMARY KEY (pk)
);

CREATE TABLE organisation_repository (
    organisation_pk INTEGER NOT NULL,
    repository_pk INTEGER NOT NULL,
    FOREIGN KEY(organisation_pk) REFERENCES organisation (pk),
    FOREIGN KEY(repository_pk) REFERENCES repository (pk)
);

CREATE TABLE setting (
    id SERIAL NOT NULL,
    key VARCHAR(32) NOT NULL,
    value VARCHAR(64) NOT NULL,
    organisation_pk INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(organisation_pk) REFERENCES organisation (pk) ON DELETE CASCADE
);

CREATE TABLE plugin_state (
    id SERIAL NOT NULL,
    plugin_id VARCHAR(32) NOT NULL,
    enabled BOOLEAN NOT NULL,
    organisation_pk INTEGER NOT NULL,
    repository_pk INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(organisation_pk) REFERENCES organisation (pk) ON DELETE CASCADE,
    FOREIGN KEY(repository_pk) REFERENCES repository (pk) ON DELETE CASCADE,
    UNIQUE (plugin_id)
);
