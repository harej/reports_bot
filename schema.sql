-- MySQL dump 10.13  Distrib 5.5.49, for debian-linux-gnu (x86_64)
--
-- Host: tools-db    Database: s52475__wpx_p
-- ------------------------------------------------------
-- Server version   5.5.39-MariaDB-log

CREATE DATABASE `wpx`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

--
-- Table structure for table `config`
--

DROP TABLE IF EXISTS `config`;
CREATE TABLE `config` (
    `config_site` VARCHAR(255) NOT NULL,
    `config_json` MEDIUMTEXT NOT NULL,
    PRIMARY KEY (`config_site`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Table structure for table `lastupdated`
--

DROP TABLE IF EXISTS `lastupdated`;
CREATE TABLE `lastupdated` (
    `lu_site` VARCHAR(255) NOT NULL,
    `lu_key` VARCHAR(255) NOT NULL,
    `lu_timestamp` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`lu_site`, `lu_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Table structure for table `base_page`
--

DROP TABLE IF EXISTS `base_page`;
CREATE TABLE `base_page` (
    `page_id` INT(8) UNSIGNED NOT NULL,
    `page_talk_id` INT(8) UNSIGNED NOT NULL,
    `page_title` VARCHAR(255) NOT NULL,
    `page_ns` INT(11) NOT NULL,
    `page_is_redirect` TINYINT(1) UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (`page_id`),
    UNIQUE KEY (`page_talk_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Table structure for table `base_project`
--

DROP TABLE IF EXISTS `base_project`;
CREATE TABLE `base_project` (
    `project_id` INT(8) UNSIGNED NOT NULL,
    `project_title` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Table structure for table `base_index`
--

DROP TABLE IF EXISTS `base_index`;
CREATE TABLE `base_index` (
    `index_id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
    `index_page` INT(8) UNSIGNED NOT NULL,
    `index_project` INT(8) UNSIGNED NOT NULL,
    PRIMARY KEY (`index_id`),
    KEY (`index_page`),
    KEY (`index_project`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dump completed on 2016-06-23  9:46:05
