create table environmental_type (
    id serial primary key,
    name varchar(255) not null
);

create table climat_type (
    id serial primary key,
    name varchar(255) not null
);

create table locations (
    id serial primary key,
    continent varchar(100),
    country varchar(100),
    city varchar(100),
    is_aquatic boolean not null,
    aquatic_zone varchar(100),
    long_format varchar(255) not null
);

create table environmental_captures (
    id serial primary key,
    ingestion_id integer references locations(id),
    timestamp timestamp not null,
    latitude double precision not null,
    longitude double precision not null,
    altitude double precision,
    location_id integer references locations(id),
    hemisphere varchar(10) not null,
    distance_equator double precision not null,
    distance_equator_km double precision not null,
    temperature double precision,
    humidity double precision,
    pressure double precision,
    luminosity double precision,
    co2_concentration double precision,
    environmental_type_id integer references environmental_type(id) not null,
    climat_type_id integer references climat_type(id) not null,
    season varchar(50) not null,
    is_night boolean not null
);

create table ingestion_runs (
    id serial primary key,
    launch_type varchar(255) not null,
    file_name varchar(255) not null,
    run_start timestamp not null,
    run_end timestamp,
    status varchar(50) not null,
    rows_ok integer not null,
    rows_ko integer not null,
    log_file_path varchar(255)
);

create table geographic_metrics (
    id serial primary key,
    location_id integer references locations(id),
    window_capture varchar(100) not null,
    avg_temperature double precision,
    max_temperature double precision,
    min_temperature double precision,
    avg_humidity double precision,
    max_humidity double precision,
    min_humidity double precision,
    avg_pressure double precision,
    avg_luminosity double precision,
    z_score_temperature double precision,
    z_score_humidity double precision,
    z_score_pressure double precision,
    z_score_luminosity double precision,
    avg_co2_ppm double precision,
    p95_co2_ppm double precision,
    t_range_c double precision,
    photoperiod_hours double precision,
    n_observations integer
);