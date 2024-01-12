import mysql.connector
import os

# Connect to the database
electoraldb = mysql.connector.connect(
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASS'),
        host='100.102.58.61',
        database='electoralsystem',
        auth_plugin='mysql_native_password'
    )
print("Connected to the database.")

## Create table called 'electionresults' in the database
cur = electoraldb.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS electionresults (
        `system` VARCHAR(255) NOT NULL,
        partyName VARCHAR(255) NOT NULL,
        votes INT NOT NULL,
        seats INT NOT NULL,
        percentage_seats VARCHAR(255) NOT NULL,
        percentage_votes VARCHAR(255) NOT NULL,
        difference_in_seats_votes VARCHAR(255) NOT NULL,
        different_from_winner VARCHAR(3) NOT NULL
    );
''')

def calculate_fptp():
    # SQL query to get winning constituency in each region and sum their votes
    cur.execute('''
            SELECT
                p.partyName AS Party,
                c.constituencyName AS Constituency,
                cd.votes AS Votes
            FROM
                candidate cd
            JOIN
                party p ON cd.partyID = p.partyID
            JOIN
                constituency c ON cd.constituencyID = c.constituencyID;
    ''')

    # Fetch the results
    data = cur.fetchall()

    # Create array of constituencies
    totalConstituencies = 0
    seats = 0
    constituencies = []
    partiesVotes = {}
    partiesSeats = {}

    for y in data:
        if y[1] not in constituencies:
            totalConstituencies += 1
            constituencies.append(y[1])

    for x in data:
        if x[0] not in partiesVotes:
            partiesVotes[x[0]] = 0

    for x in data:
        if x[0] not in partiesSeats:
            partiesSeats[x[0]] = 0

    for x in constituencies:
        constituencyVotes = 0
        winningParty = ""
        winningVotes = 0
        for y in data:
            if y[1] == x:
                constituencyVotes += y[2]
                if y[2] > winningVotes:
                    winningParty = y[0]
                    winningVotes = y[2]

        partiesVotes[winningParty] += winningVotes
        partiesSeats[winningParty] += 1

    for x in data:
        partiesVotes[x[0]] += x[2]

    total_votes = sum(partiesVotes.values())
    most_seats = max(partiesSeats, key=partiesSeats.get)

    data_unsorted = {
        party: {
            'votes': partiesVotes[party], 
            'seats': partiesSeats[party], 
            'percentage_seats': "{:.2f}%".format(partiesSeats[party] / totalConstituencies * 100),  
            'percentage_votes': "{:.2f}%".format(partiesVotes[party] / total_votes * 100),
            'difference_in_seats_votes': "{:.2f}%".format(abs((partiesSeats[party] / totalConstituencies - partiesVotes[party] / total_votes) * 100)),
            'different_from_winner': 'Yes' if party == most_seats else 'No'
        } 
        for party in partiesSeats.keys()
    }
    ## Insert data into the table
    for party in data_unsorted.keys():
        cur.execute('''
            INSERT INTO electionresults VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        ''', (
            'First Past The Post',  # replace with actual system name
            party,
            data_unsorted[party]['votes'],
            data_unsorted[party]['seats'],
            data_unsorted[party]['percentage_seats'],
            data_unsorted[party]['percentage_votes'],
            data_unsorted[party]['difference_in_seats_votes'],
            data_unsorted[party]['different_from_winner']
        ))

    electoraldb.commit()

def calculate_spr(level=None, threshold=None):
    if level == 'All Seats':
        print("Calculating All Seats results.")
        if threshold:
            print("Threshold: " + str(threshold) + "%.")
    elif level in ['County', 'Region', 'Country']:
        print("Calculating " + level + " results.")

calculate_fptp()
print("Finished calculating FPTP results.")

# Make a Loop through calculate_spr() for each level and threshold. All Seats, All Seats 5%, County, Region, Country.

levls = [['All Seats', None], ['All Seats 5%', 5], ['County', None], ['Region', None], ['Country', None]]
for level in levls:
    calculate_spr(level[0], level[1])
    print("Finished calculating " + level[0] + " results.")

cur.close()
electoraldb.close()