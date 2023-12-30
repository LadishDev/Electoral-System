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

CREATE TABLE temp_table (
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

/* INSERT DATA FROM TEMPORARY TABLE INTO DATABASE TABLES */

-- Insert data into county table
INSERT INTO county (countyName)
SELECT DISTINCT countyName FROM temp_table;

-- Insert data into region table
INSERT INTO region (regionName)
SELECT DISTINCT regionName FROM temp_table;

-- Insert data into country table
INSERT INTO country (countryName)
SELECT DISTINCT countryName FROM temp_table;

-- Insert data into constituency table (handling duplicates)
INSERT IGNORE INTO constituency (constituencyName, constituencyType, sittingmp, countyID, regionID, countryID)
SELECT DISTINCT t.constituencyName, t.constituencyType, t.sittingmp, c.countyID, r.regionID, co.countryID
FROM temp_table t
JOIN county c ON t.countyName = c.countyName
JOIN region r ON t.regionName = r.regionName
JOIN country co ON t.countryName = co.countryName;

-- Insert data into party table
INSERT INTO party (partyName)
SELECT DISTINCT PartyName FROM temp_table;

-- Insert data into candidate table (handling duplicates)
INSERT IGNORE INTO candidate (firstname, surname, gender, partyID, constituencyID)
SELECT
    t.firstname,
    t.surname,
    t.gender,
    (SELECT p.partyID FROM party p WHERE t.PartyName = p.partyName LIMIT 1),
    (SELECT con.constituencyID FROM constituency con WHERE t.constituencyName = con.constituencyName LIMIT 1)
FROM temp_table t
GROUP BY
    t.firstname,
    t.surname,
    t.gender,
    t.PartyName,
    t.constituencyName;

-- Insert data into electionresults table
INSERT IGNORE INTO electionresults (constituencyID, partyID)
SELECT 
    (SELECT con.constituencyID FROM constituency con WHERE t.constituencyName = con.constituencyName LIMIT 1),
    (SELECT p.partyID FROM party p WHERE t.PartyName = p.partyName LIMIT 1),
    t.votes
FROM temp_table t;

-- Drop the Temporary Table
DROP TABLE temp_table;