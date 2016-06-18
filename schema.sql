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
    `json` mediumtext
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Table structure for table `lastupdated`
--

DROP TABLE IF EXISTS `lastupdated`;
CREATE TABLE `lastupdated` (
    `lu_key` varchar(255) DEFAULT NULL,
    `lu_timestamp` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Table structure for table `index_base`
--

DROP TABLE IF EXISTS `index_base`;
CREATE TABLE `index_base` (
    `pi_id` int(11) NOT NULL AUTO_INCREMENT,
    `pi_page` varchar(255) DEFAULT NULL,
    `pi_project` varchar(255) DEFAULT NULL,
    PRIMARY KEY (`pi_id`),
    KEY `projectindex_pageindex` (`pi_page`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dump completed on 2016-06-18  0:07:05
