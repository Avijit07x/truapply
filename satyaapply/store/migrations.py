MIGRATIONS: tuple[str, ...] = (
    """
    create table jobs (
        id integer primary key,
        key text not null unique,
        dupe text not null,
        source text not null,
        url text not null,
        apply_url text not null,
        company text not null,
        title text not null,
        location text not null default '',
        description text not null default '',
        posted_at text,
        found_at text not null,
        status text not null default 'new',
        status_at text not null,
        note text
    );
    create index jobs_dupe on jobs (dupe);
    create index jobs_status on jobs (status);
    """,
    """
    alter table jobs add column score integer;
    alter table jobs add column resume_pdf text;
    alter table jobs add column sent text;
    alter table jobs add column applied_at text;
    create table boards (
        ats text not null,
        slug text not null,
        company text not null default '',
        origin text not null,
        added_at text not null,
        checked_at text,
        dead integer not null default 0,
        primary key (ats, slug)
    );
    create table answers (
        question text primary key,
        answer text not null,
        source text not null,
        updated_at text not null
    );
    create table questions (
        question text primary key,
        label text not null,
        job_id integer references jobs (id),
        asked_at text not null
    );
    create table meta (
        key text primary key,
        value text not null
    );
    """,
    """
    alter table jobs add column reason text;
    update jobs set reason = note where score is not null and status in ('scored', 'skipped');
    """,
)
