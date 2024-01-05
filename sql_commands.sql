-- SQL COMMANDS TO CREATE THE DATABASE AND STORE THE DATASET INTO THE DATABASE TABLES

/* CREATE DATABASE AND SET AS DEFAULT */
CREATE SCHEMA `electoralsystem` ;
USE electoralsystem;

/* CREATE DATABASE TABLES */
CREATE TABLE county (
    countyID INT PRIMARY KEY AUTO_INCREMENT,
    countyName VARCHAR(24)
);

CREATE TABLE region (
    regionID INT PRIMARY KEY AUTO_INCREMENT,
    regionName VARCHAR(24)
);

CREATE TABLE country (
    countryID INT PRIMARY KEY AUTO_INCREMENT,
    countryName VARCHAR(16)
);

CREATE TABLE constituency (
    constituencyID INT PRIMARY KEY AUTO_INCREMENT,
    constituencyName VARCHAR(46),
    constituencyType VARCHAR(8),
    sittingmp VARCHAR(4),
    countyID INT,
    FOREIGN KEY (countyID) REFERENCES county(countyID),
    regionID INT,
    FOREIGN KEY (regionID) REFERENCES region(regionID),
    countryID INT,
    FOREIGN KEY (countryID) REFERENCES country(countryID)
);

CREATE TABLE party (
    partyID INT PRIMARY KEY AUTO_INCREMENT,
    partyName VARCHAR(51)
);

CREATE TABLE candidate (
    candidateID INT PRIMARY KEY AUTO_INCREMENT,
    firstname VARCHAR(51),
    surname VARCHAR(51),
    gender CHAR(11),
    partyID INT,
    FOREIGN KEY (partyID) REFERENCES party(partyID),
    constituencyID INT,
    FOREIGN KEY (constituencyID) REFERENCES constituency(constituencyID)
);

CREATE TABLE electionresults (
    resultID INT PRIMARY KEY AUTO_INCREMENT,
    constituencyID INT,
    FOREIGN KEY (constituencyID) REFERENCES constituency(constituencyID),
    partyID INT,
    FOREIGN KEY (partyID) REFERENCES party(partyID),
    votes INT
);  

/* INSERT CSV DATA INTO TEMPORARY TABLE */

CREATE TEMPORARY TABLE temp_table (
    tempID INT PRIMARY KEY AUTO_INCREMENT,
    constituencyName VARCHAR(46),
    countyName VARCHAR(24),
    regionName VARCHAR(24),
    countryName VARCHAR(16),
    constituencyType VARCHAR(8),
    PartyName VARCHAR(51),
    firstname VARCHAR(50),
    surname VARCHAR(50),
    gender CHAR(11),
    sittingmp VARCHAR(4),
    votes INT
);

LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/data.csv'
INTO TABLE temp_table
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(constituencyName, countyName, regionName, countryName, constituencyType, PartyName, firstname, surname, gender, sittingmp, votes);

/* INSERT DATA FROM TEMPORARY TABLE INTO DATABASE TABLES SQL COMMANDS */

-- Insert data into country, region, county, and party tables
INSERT INTO country (countryName)
SELECT DISTINCT countryName FROM temp_table;

INSERT INTO region (regionName)
SELECT DISTINCT regionName FROM temp_table;

INSERT INTO county (countyName)
SELECT DISTINCT countyName FROM temp_table;

INSERT INTO party (partyName)
SELECT DISTINCT PartyName FROM temp_table;

-- Insert data into constituency table
INSERT INTO constituency (constituencyName, constituencyType, sittingmp, countyID, regionID, countryID)
SELECT
    temp_table.constituencyName,
    temp_table.constituencyType,
    temp_table.sittingmp,
    county.countyID,
    region.regionID,
    country.countryID 
FROM temp_table
LEFT JOIN county ON temp_table.countyName = county.countyName
LEFT JOIN region ON temp_table.regionName = region.regionName
LEFT JOIN country ON temp_table.countryName = country.countryName;


-- Insert data into candidate table
INSERT INTO candidate (firstname, surname, gender, partyID, constituencyID)
SELECT
    temp_table.firstname,
    temp_table.surname,
    temp_table.gender,
    MAX(party.partyID) AS partyID,
    MAX(constituency.constituencyID) AS constituencyID
FROM temp_table
LEFT JOIN party ON temp_table.partyName = party.partyName
LEFT JOIN constituency ON temp_table.constituencyName = constituency.constituencyName
GROUP BY temp_table.firstname, temp_table.surname, temp_table.gender, temp_table.tempID;

-- Insert data into election results table
INSERT INTO electionresults (constituencyID, partyID, votes)
SELECT
    MAX(constituency.constituencyID) AS constituencyID,
    MAX(party.partyID) AS partyID,
    SUM(temp_table.votes) AS total_votes
FROM temp_table
LEFT JOIN constituency ON temp_table.constituencyName = constituency.constituencyName
LEFT JOIN party ON temp_table.partyName = party.partyName
GROUP BY temp_table.constituencyName, temp_table.partyName, temp_table.votes;

-- Drop temporary table
DROP TEMPORARY TABLE IF EXISTS temp_table;

SELECT 'Database tables have been created and populated successfully.' AS 'Message';
