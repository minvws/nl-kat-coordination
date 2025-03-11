SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_table_access_method = heap;

CREATE TYPE public.taskstatus AS ENUM (
    'PENDING',
    'QUEUED',
    'DISPATCHED',
    'RUNNING',
    'COMPLETED',
    'FAILED'
);

ALTER TYPE public.taskstatus OWNER TO mula_dba;

GRANT ALL ON TYPE public.taskstatus TO mula;

CREATE TABLE public.items (
    id uuid NOT NULL,
    scheduler_id character varying,
    hash varchar(32),
    priority integer,
    data json NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    modified_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.items OWNER TO mula_dba;

GRANT ALL ON TABLE public.items TO mula;

CREATE TABLE public.tasks (
    id uuid NOT NULL,
    scheduler_id character varying,
    status public.taskstatus NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    modified_at timestamp with time zone DEFAULT now() NOT NULL,
    p_item json NOT NULL,
    type character varying
);

ALTER TABLE public.tasks OWNER TO mula_dba;

GRANT ALL ON TABLE public.tasks TO mula;

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);
