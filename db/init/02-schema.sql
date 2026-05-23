-- Heart on a Sleeve - Full Initial Schema
-- Run after 01-init.sql

-- Design projects
CREATE TABLE design_projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',
    merch_type VARCHAR(50) NOT NULL,
    bbox GEOMETRY(POLYGON, 4326) NOT NULL,
    aspect_ratio_x INT NOT NULL,
    aspect_ratio_y INT NOT NULL,
    print_width_px INT NOT NULL,
    print_height_px INT NOT NULL,
    svg_path VARCHAR(500),
    stl_path VARCHAR(500),
    license_data JSONB DEFAULT '{}',
    woocommerce_product_id VARCHAR(100),
    pod_order_id VARCHAR(100),
    pod_provider VARCHAR(50),
    style VARCHAR(50) DEFAULT 'osm_default',
    include_labels BOOLEAN DEFAULT TRUE,
    include_roads BOOLEAN DEFAULT TRUE,
    include_parks BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_design_bbox ON design_projects USING GIST(bbox);

-- OSM data cache (24hr TTL)
CREATE TABLE osm_data_cache (
    id SERIAL PRIMARY KEY,
    bbox GEOMETRY(POLYGON, 4326) NOT NULL,
    zoom_level INT NOT NULL,
    raw_json JSONB NOT NULL,
    element_count INT NOT NULL,
    license_info JSONB NOT NULL,
    fetched_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);
CREATE INDEX idx_osm_cache_bbox ON osm_data_cache USING GIST(bbox);
CREATE INDEX idx_osm_cache_expires ON osm_data_cache (expires_at);

-- Individual design elements
CREATE TABLE design_elements (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES design_projects(id) ON DELETE CASCADE,
    element_type VARCHAR(50) NOT NULL,
    geometry GEOMETRY(GEOMETRY, 4326) NOT NULL,
    style_params JSONB DEFAULT '{}',
    z_index INT DEFAULT 0,
    svg_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_elements_project ON design_elements(project_id);
CREATE INDEX idx_elements_geometry ON design_elements USING GIST(geometry);

-- POD orders
CREATE TABLE pod_orders (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES design_projects(id),
    provider VARCHAR(50) NOT NULL,
    external_order_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    product_sku VARCHAR(255),
    quantity INT DEFAULT 1,
    price_gbp NUMERIC(10, 2),
    tracking_number VARCHAR(255),
    tracking_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- License audit trail
CREATE TABLE license_audit (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES design_projects(id),
    data_source VARCHAR(100) NOT NULL,
    license_type VARCHAR(50) NOT NULL,
    attribution_text TEXT,
    compliant BOOLEAN DEFAULT TRUE,
    checked_at TIMESTAMP DEFAULT NOW()
);