<div align='center'>

<h1>To calculate election results for seats for a few different methods.</h1>
<p>A electoral system with a SQL database</p>

<h4> <span> · </span> <a href="https://github.com/LadishDev/Electoral-System/blob/master/README.md"> Documentation </a> <span> · </span> <a href="https://github.com/LadishDev/Electoral-System/issues"> Report Bug </a> <span> · </span> <a href="https://github.com/LadishDev/Electoral-System/issues"> Request Feature </a> </h4>


</div>

# :notebook_with_decorative_cover: Table of Contents

- [About the Project](#star2-about-the-project)
- [License](#warning-license)
- [Contact](#handshake-contact)


## :star2: About the Project
<details> <summary>Database</summary> <ul>
<li><a href="100.102.58.61">electoralsystem</a></li>
</ul> </details>

### :art: Color Reference
| Color | Hex |
| --------------- | ---------------------------------------------------------------- |
| Primary Color | ![#bb38db](https://via.placeholder.com/10/bb38db?text=+) #bb38db |
| Secondary Color | ![#393E46](https://via.placeholder.com/10/393E46?text=+) #393E46 |
| Accent Color | ![#00ADB5](https://via.placeholder.com/10/00ADB5?text=+) #00ADB5 |
| Text Color | ![#EEEEEE](https://via.placeholder.com/10/EEEEEE?text=+) #EEEEEE |

### :key: Environment Variables
To run this project, you will need to add the following environment variables to your .env file

`DB_USER`


`DB_PASS`




## :toolbox: Getting Started

### :bangbang: Prerequisites


- Install MySQL Server<a href="https://dev.mysql.com/downloads/mysql/"> Here</a>
```bash
sudo dnf install mysql-community-server
```

- Install Python<a href="https://www.python.org/downloads/"> Here</a>
```bash
sudo dnf install python
```



### :gear: Installation


Flask
```bash
pip install flask
```

mysql-connector
```bash
pip install mysql-connector-python
```



### :running: Run Locally

Clone the project

```bash
https://github.com/LadishDev/Electoral-System
```

Go to Project Directory
```bash
cd Electoral-System
```

Setup MySQL server with Scheme and data
```bash
mysql -uladish -p < /Documents/Electoral-System/sql-commands.sql
```

Start the python script to calculate results and host web server
```bash
python .\electoral-system.py
```



## :warning: License

Distributed under the no License. See LICENSE.txt for more information.

## :handshake: Contact

Callum - developer@ladish.dev

Project Link: [https://github.com/LadishDev/Electoral-System](https://github.com/LadishDev/Electoral-System)