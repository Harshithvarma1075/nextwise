CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT UNSIGNED NOT NULL,
    age TINYINT UNSIGNED NOT NULL,
    gender CHAR(1) NOT NULL,
    PRIMARY KEY (user_id),
    CONSTRAINT chk_users_age CHECK (age BETWEEN 1 AND 120),
    CONSTRAINT chk_users_gender CHECK (gender IN ('F', 'M'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS products (
    item_id CHAR(36) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    category_l1 VARCHAR(64) NOT NULL,
    category_l2 VARCHAR(128) NOT NULL,
    product_name VARCHAR(512) NOT NULL,
    product_description TEXT NOT NULL,
    gender VARCHAR(3) NOT NULL,
    promoted_status VARCHAR(7) NOT NULL,
    PRIMARY KEY (item_id),
    CONSTRAINT chk_products_price CHECK (price > 0),
    CONSTRAINT chk_products_gender CHECK (gender IN ('F', 'M', 'ANY')),
    CONSTRAINT chk_products_promoted CHECK (promoted_status IN ('true', 'unknown'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS interactions (
    interaction_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    item_id CHAR(36) NOT NULL,
    event_type VARCHAR(16) NOT NULL,
    timestamp_unix BIGINT UNSIGNED NOT NULL,
    event_timestamp DATETIME NOT NULL,
    discount_applied BOOLEAN NOT NULL,
    PRIMARY KEY (interaction_id),
    CONSTRAINT uq_interactions_natural UNIQUE (user_id, item_id, event_type, timestamp_unix),
    CONSTRAINT fk_interactions_user FOREIGN KEY (user_id) REFERENCES users (user_id),
    CONSTRAINT fk_interactions_product FOREIGN KEY (item_id) REFERENCES products (item_id),
    CONSTRAINT chk_interactions_event CHECK (event_type IN ('View', 'AddToCart', 'ViewCart', 'StartCheckout', 'Purchase')),
    CONSTRAINT chk_interactions_timestamp CHECK (timestamp_unix > 0),
    INDEX idx_interactions_user_time (user_id, timestamp_unix),
    INDEX idx_interactions_item_time (item_id, timestamp_unix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
