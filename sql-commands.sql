CREATE SCHEMA `electoralsystem` ;

USE electoralsystem;

CREATE TABLE constituency (
    constituencyID INT PRIMARY KEY,
    constituencyName VARCHAR(45),
    countyName VARCHAR(23),
    regionName VARCHAR(23),
    countryName VARCHAR(14),
    constituencyType VARCHAR(7),
    sittingmp BOOLEAN
)

CREATE TABLE party (
    partyID INT PRIMARY KEY,
    partyName VARCHAR(50)
)

CREATE TABLE candidate (
    candidateID INT PRIMARY KEY,
    firstname VARCHAR(50),
    surname VARCHAR(50),
    gender CHAR(1),
    partyID INT,
    FOREIGN KEY (partyID) REFERENCES party(partyID),
    constituencyID INT,
    FOREIGN KEY (constituencyID) REFERENCES constituency(constituencyID)
)

CREATE TABLE electionresults (
    resultID INT PRIMARY KEY,
    constituencyID INT,
    FOREIGN KEY (constituencyID) REFERENCES constituency(constituencyID),
    partyID INT,
    FOREIGN KEY (partyID) REFERENCES party(partyID),
)


