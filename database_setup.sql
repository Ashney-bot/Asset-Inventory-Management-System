CREATE DATABASE IF NOT EXISTS `asset inventory management system`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `asset inventory management system`;

CREATE TABLE IF NOT EXISTS `categories` (
    `category_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    PRIMARY KEY (`category_id`),
    UNIQUE KEY `uq_categories_name` (`name`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `suppliers` (
    `supplier_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(150) NOT NULL,
    PRIMARY KEY (`supplier_id`),
    UNIQUE KEY `uq_suppliers_name` (`name`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `locations` (
    `location_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(150) NOT NULL,
    PRIMARY KEY (`location_id`),
    UNIQUE KEY `uq_locations_name` (`name`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `users` (
    `user_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(100) NOT NULL,
    `email` VARCHAR(150) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('Admin', 'Staff') NOT NULL DEFAULT 'Staff',
    `access_status` ENUM('Pending', 'Active', 'Denied') NOT NULL DEFAULT 'Pending',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`user_id`),
    UNIQUE KEY `uq_users_username` (`username`),
    UNIQUE KEY `uq_users_email` (`email`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `password_reset_requests` (
    `request_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` INT UNSIGNED NOT NULL,
    `status` ENUM('Pending', 'Approved', 'Denied') NOT NULL DEFAULT 'Pending',
    `requested_password_hash` VARCHAR(64) NULL,
    `requested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `resolved_at` TIMESTAMP NULL,
    PRIMARY KEY (`request_id`),
    KEY `idx_password_reset_user` (`user_id`),
    CONSTRAINT `fk_reset_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `assets` (
    `asset_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `asset_name` VARCHAR(150) NOT NULL,
    `brand` VARCHAR(100) NOT NULL,
    `category_id` INT UNSIGNED NOT NULL,
    `quantity` INT UNSIGNED NOT NULL DEFAULT 1,
    `unit_price` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `status` ENUM('In Stock', 'Disposed') NOT NULL DEFAULT 'In Stock',
    `purchase_date` DATE NULL,
    `warranty_duration` VARCHAR(50) NULL,
    `supplier_id` INT UNSIGNED NULL,
    `location_id` INT UNSIGNED NULL,
    `created_by` INT UNSIGNED NULL,
    `deleted_at` TIMESTAMP NULL DEFAULT NULL,
    `deleted_by` INT UNSIGNED NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`asset_id`),
    KEY `idx_assets_category` (`category_id`),
    KEY `idx_assets_supplier` (`supplier_id`),
    KEY `idx_assets_location` (`location_id`),
    KEY `idx_assets_status` (`status`),
    CONSTRAINT `fk_assets_category`
        FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT `fk_assets_supplier`
        FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`supplier_id`)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT `fk_assets_location`
        FOREIGN KEY (`location_id`) REFERENCES `locations` (`location_id`)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT `fk_assets_created_by`
        FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT `fk_assets_deleted_by`
        FOREIGN KEY (`deleted_by`) REFERENCES `users` (`user_id`)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT `chk_assets_quantity` CHECK (`quantity` >= 0),
    CONSTRAINT `chk_assets_unit_price` CHECK (`unit_price` >= 0)
) ENGINE=InnoDB;

-- Convert former maintenance assets and remove the Maintenance status from existing databases.
UPDATE `assets`
SET `status` = 'In Stock'
WHERE `status` = 'In Maintenance';

ALTER TABLE `assets`
MODIFY COLUMN `status` ENUM('In Stock', 'Disposed') NOT NULL DEFAULT 'In Stock';

-- Remove the legacy serial-number column from existing installations[cite: 21].
DROP PROCEDURE IF EXISTS migrate_assets_remove_serial_number;
DELIMITER //
CREATE PROCEDURE migrate_assets_remove_serial_number()
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = 'assets'
          AND index_name = 'uq_assets_serial_number'
    ) THEN
        ALTER TABLE assets DROP INDEX uq_assets_serial_number;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'assets'
          AND column_name = 'serial_number'
    ) THEN
        ALTER TABLE assets DROP COLUMN serial_number;
    END IF;
END//
DELIMITER ;
CALL migrate_assets_remove_serial_number();
DROP PROCEDURE migrate_assets_remove_serial_number;

-- Add soft-delete fields to databases created before the Bin feature[cite: 21].
DROP PROCEDURE IF EXISTS migrate_assets_add_bin_fields;
DELIMITER //
CREATE PROCEDURE migrate_assets_add_bin_fields()
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'assets'
          AND column_name = 'deleted_at'
    ) THEN
        ALTER TABLE assets ADD COLUMN deleted_at TIMESTAMP NULL DEFAULT NULL AFTER created_by;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'assets'
          AND column_name = 'deleted_by'
    ) THEN
        ALTER TABLE assets ADD COLUMN deleted_by INT UNSIGNED NULL AFTER deleted_at;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema = DATABASE()
          AND table_name = 'assets'
          AND constraint_name = 'fk_assets_deleted_by'
    ) THEN
        ALTER TABLE assets
            ADD CONSTRAINT fk_assets_deleted_by
            FOREIGN KEY (deleted_by) REFERENCES users (user_id)
            ON UPDATE CASCADE ON DELETE SET NULL;
    END IF;
END//
DELIMITER ;
CALL migrate_assets_add_bin_fields();
DROP PROCEDURE migrate_assets_add_bin_fields;

CREATE TABLE IF NOT EXISTS `activity_logs` (
    `log_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` INT UNSIGNED NULL,
    `username` VARCHAR(100) NOT NULL,
    `role` ENUM('Admin', 'Staff', 'System') NOT NULL DEFAULT 'System',
    `action` VARCHAR(20) NOT NULL,
    `description` TEXT NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`log_id`),
    KEY `idx_activity_logs_user` (`user_id`),
    KEY `idx_activity_logs_action` (`action`),
    KEY `idx_activity_logs_created_at` (`created_at`),
    CONSTRAINT `fk_activity_logs_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT `chk_activity_logs_action`
        CHECK (`action` IN ('CREATE', 'READ', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `notifications` (
    `notification_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` INT UNSIGNED NULL,
    `title` VARCHAR(150) NOT NULL,
    `message` VARCHAR(500) NOT NULL,
    `is_read` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`notification_id`),
    KEY `idx_notifications_user` (`user_id`, `is_read`),
    CONSTRAINT `fk_notifications_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

INSERT INTO `categories` (`name`) VALUES
    ('IT hardware'),
    ('Networking & Infrastructures'),
    ('Peripherals & Accesories'),
    ('AV & Media')
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

-- Initial password: admin123
INSERT INTO `users` (`username`, `email`, `password_hash`, `role`, `access_status`)
SELECT 'admin', 'admin@example.com',
       SHA2('admin123', 256),
       'Admin', 'Active'
WHERE NOT EXISTS (
    SELECT 1 FROM `users` WHERE `username` = 'admin' OR `email` = 'admin@example.com'
);