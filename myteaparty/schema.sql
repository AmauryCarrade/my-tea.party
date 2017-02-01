SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT=0;
START TRANSACTION;
SET time_zone = "+00:00";

--
-- Database: `teaparty`
--

-- --------------------------------------------------------

--
-- Table structure for table `tea_lists`
--

CREATE TABLE IF NOT EXISTS `tea_lists` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `key` varchar(100) CHARACTER SET utf8 NOT NULL COMMENT 'A sharing key for this tea list (read&write)',
  `creator_ip` binary(128) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `tea_lists_items`
--

CREATE TABLE IF NOT EXISTS `tea_lists_items` (
  `list_id` int(11) NOT NULL,
  `tea_id` int(11) NOT NULL,
  `is_empty` tinyint(1) NOT NULL DEFAULT '0',
  KEY `list_id` (`list_id`),
  KEY `tea_id` (`tea_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- RELATIONS FOR TABLE `tea_lists_items`:
--   `list_id`
--       `tea_lists` -> `id`
--   `tea_id`
--       `tea_teas` -> `id`
--

-- --------------------------------------------------------

--
-- Table structure for table `tea_teas`
--

CREATE TABLE IF NOT EXISTS `tea_teas` (
  `id` int(10) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8 NOT NULL COMMENT 'The tea name, as displayed in the titles',
  `vendor` int(10) NOT NULL COMMENT 'The tea vendor ID',
  `vendor_id` varchar(30) CHARACTER SET utf8 DEFAULT NULL COMMENT 'The vendor''s own tea ID, e.g. 7004 for Mariage Frères''s Paris Breakfast Tea',
  `slug` varchar(100) CHARACTER SET utf8 NOT NULL COMMENT 'The tea slug as visible in the URL',
  `description` varchar(256) CHARACTER SET utf8 DEFAULT NULL COMMENT 'A small description for the tea (one line), displayed as subtitle',
  `long_description` text CHARACTER SET utf8 COMMENT 'A long description for the tea, can be extanded over multiple paragraphs',
  `ingredients` text CHARACTER SET utf8 COMMENT 'Coma-separated list of ingredients, if supplied',
  `tips_raw` text CHARACTER SET utf8 COMMENT 'The raw preparation tips, displayed if the analysis fails',
  `tips_mass` mediumint(7) DEFAULT NULL COMMENT 'The advised mass in mg',
  `tips_volume` smallint(6) DEFAULT NULL COMMENT 'The advised volume in cL',
  `tips_temperature` smallint(6) DEFAULT NULL COMMENT 'The advised temperature in °C',
  `tips_duration` smallint(6) DEFAULT NULL COMMENT 'The advised duration in seconds',
  `illustration` varchar(70) CHARACTER SET utf8 DEFAULT NULL COMMENT 'A reference to the tea illustration',
  `price` float DEFAULT NULL COMMENT 'The price as seen in the vendor page (euros)',
  `price_unit` varchar(100) CHARACTER SET utf8 DEFAULT NULL COMMENT 'The amount of tea sold for the stored price (e.g. “100 g.”)',
  `link` varchar(256) CHARACTER SET utf8 NOT NULL COMMENT 'A link to the tea vendor page',
  `updated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'The last crawl date',
  `deleted` timestamp NULL DEFAULT NULL COMMENT 'NULL if not deleted',
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  KEY `vendor` (`vendor`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1;

--
-- RELATIONS FOR TABLE `tea_teas`:
--   `vendor`
--       `tea_vendors` -> `id`
--

-- --------------------------------------------------------

--
-- Table structure for table `tea_teas_types`
--

CREATE TABLE IF NOT EXISTS `tea_teas_types` (
  `tea_id` int(11) NOT NULL,
  `type_id` int(11) NOT NULL,
  PRIMARY KEY (`tea_id`,`type_id`),
  KEY `type_id` (`type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- RELATIONS FOR TABLE `tea_teas_types`:
--   `type_id`
--       `tea_types` -> `id`
--   `tea_id`
--       `tea_teas` -> `id`
--

-- --------------------------------------------------------

--
-- Table structure for table `tea_types`
--

CREATE TABLE IF NOT EXISTS `tea_types` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `order` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `tea_vendors`
--

CREATE TABLE IF NOT EXISTS `tea_vendors` (
  `id` int(6) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8 NOT NULL COMMENT 'The vendor name, displayed as a title or in texts',
  `slug` varchar(32) CHARACTER SET utf8 NOT NULL COMMENT 'The vendor slug used in the URLs as an identifier',
  `description` varchar(255) CHARACTER SET utf8 NOT NULL COMMENT 'A small description for this vendor',
  `logo` varchar(70) CHARACTER SET utf8 DEFAULT NULL COMMENT 'A reference to this vendor''s logo',
  `link` varchar(255) CHARACTER SET utf8 NOT NULL COMMENT 'A link to the vendor''s homepage',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`,`link`),
  UNIQUE KEY `slug` (`slug`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1;

--
-- Constraints for tables
--

--
-- Constraints for table `tea_lists_items`
--
ALTER TABLE `tea_lists_items`
  ADD CONSTRAINT `tea_lists_items_ibfk_1` FOREIGN KEY (`list_id`) REFERENCES `tea_lists` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `tea_lists_items_ibfk_2` FOREIGN KEY (`tea_id`) REFERENCES `tea_teas` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `tea_teas`
--
ALTER TABLE `tea_teas`
  ADD CONSTRAINT `tea_teas_ibfk_1` FOREIGN KEY (`vendor`) REFERENCES `tea_vendors` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `tea_teas_types`
--
ALTER TABLE `tea_teas_types`
  ADD CONSTRAINT `tea_teas_types_ibfk_2` FOREIGN KEY (`type_id`) REFERENCES `tea_types` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `tea_teas_types_ibfk_1` FOREIGN KEY (`tea_id`) REFERENCES `tea_teas` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;
