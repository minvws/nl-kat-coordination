# Installatiehandleiding OpenKAT

OpenKAT is een modulair framework om informatiesystemen te monitoren, registreren en analyseren. Deze installatiehandleiding bevat alle informatie die je nodig hebt om aan de slag te kunnen met OpenKAT. 

Voor het realiseren van je eigen OpenKAT installatie zijn er meerdere opties beschikbaar. Naast de installatie volgens deze handleiding zijn er docker images beschikbaar en wordt er gewerkt aan debian packages: https://github.com/minvws/nl-kat-coordination/wiki/Infrastructuur-en-voorbeeldinstallatie

## 1. Benodigdheden
Je hebt de volgende dingen nodig om  OpenKAT te installeren: 

- Een computer met een Linux-installatie. In dit document gebruiken we Ubuntu, maar op veel andere distributies werkt het op een vergelijkbare manier. Later voegen we ook instructies toe voor MacOS.
- Docker. Als je dit nog niet hebt, installeer je dit eerst in hoofdstuk 2.
- De GitHub-repository van OpenKAT: [https://github.com/minvws/nl-kat-coordination/](https://github.com/minvws/nl-kat-coordination/) 

## 2. Vóór de installatie
OpenKAT wordt geïnstalleerd in Docker, en daarom moet Docker eerst worden geïnstalleerd. Doe dit volgens de instructies van je (Unix-)besturingssysteem. De instructies voor Ubuntu lees je hieronder. Op de [website van Docker](https://docs.docker.com/engine/install/) zie je installatie-instructies voor andere distributies.

### 3.1 Docker installeren
Open een terminal naar keuze, zoals gnome-terminal op Ubuntu. (Uitleg over hoe terminal werkt wellicht?)

1. We gaan er niet van uit dat je oudere versies van Docker hebt draaien, maar als dit wel zo is moet je ze verwijderen met de volgende opdracht:
```console
$ sudo apt-get remove docker docker-engine docker.io containerd runc yarnpkg
```
Als apt-get niet doorloopt vanwege missing packages, probeer het commando dan nogmaals zonder de naam waarover apt-get struikelde.

2. Daarna installeer je enkele vereiste packages waarmee *apt* packages via HTTPS kan gebruiken:
```console
$ sudo apt-get install apt-transport-https ca-certificates curl gnupg lsb-release
```
De packages worden gecontroleerd en waar nodig bijgewerkt. Als er een installatie nodig is, vraagt apt of je door wilt gaan met de installatie ('Do you want to continue?'). Typ 'Y' en druk op enter.
3. Vervolgens voeg je de officiële GPG-sleutel van Docker toe:
```console
$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
$ echo  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```
4. Update je packages en installeer de nieuwste versie van Docker met de volgende opdrachten: 
```console
$ sudo apt-get update
$ sudo apt-get install docker-ce docker-ce-cli containerd.io
$ sudo usermod -aG docker ${USER}
```
Bij de vraag of je door wilt gaan met de installatie typ je weer 'Y' en druk je op enter. 

### 3.2 Docker-compose installeren
Installeer de nieuwste versie van docker-compose en geef de tool de juiste rechten met de volgende twee opdrachten:
```console
$ sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
$ sudo chmod +x /usr/local/bin/docker-compose
```
### 3.3 Dependencies installeren

[comment]: # (eventueel uitleggen welke packages het allemaal zijn)

Dependencies zijn packages die nodig zijn voor de werking van OpenKAT. Voer de volgende opdrachten uit om ze te installeren:
```console
$ curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
$ sudo apt-get install -y nodejs gcc g++ make python3-pip docker-compose
$ curl -sL https://dl.yarnpkg.com/debian/pubkey.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/yarnkey.gpg >/dev/null
$ echo "deb [signed-by=/usr/share/keyrings/yarnkey.gpg] https://dl.yarnpkg.com/debian stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
$ sudo apt-get update && sudo apt-get install yarn
```
## 4. Aan de slag
Nu kan de installatie van OpenKAT beginnen. Dit doen we via git,

### 4.1. Standaard installatie
1. Kloon de repository met de volgende opdracht:
```console
$ git clone https://github.com/minvws/nl-kat-coordination.git
```
2. Ga naar de map die is aangemaakt:
```console
$ cd nl-kat-coordination
```
3. Bouw OpenKAT met de volgende opdracht:
```console
$ make kat
```
Andere opties zijn 'make clone' en 'make pull' om alleen te clonen, danwel de repositories te updaten. bovenstaand commando voert dit zelf ook uit.

**LET OP:** Momenteel werkt de make kat instructie alleen voor de eerste gebruiker op een *nix systeem. Dit is een bekend probleem dat zsm opgelost zal worden. De huidige gebruiker dient gebruiker 1000 te zijn. Je kunt dit controleren door `id` uit te voeren. 

**LET OP:** in sommige gevallen lukt dit niet omdat Docker je gebruikersnaam nog niet kent. Dit los je op met de volgende opdrachten, waarbij je voor $USER je gebruikersnaam invoert:
```console
$ sudo gpasswd -a $USER docker
$ newgrp docker
```
Vervolgens wordt OpenKAT gebouwd, inclusief alle onderdelen zoals Octopoes en Rocky. 

### 4.2. Specifieke builds
Als je een specifieke build wilt maken, heb je een aantal opties. Je kunt ook in de [Makefile](https://github.com/minvws/nl-kat-coordination/blob/main/Makefile) kijken. Hieronder staat een aantal voorbeelden.

*Alleen relevante repositories klonen*
```console
$ make clone
```
*Een losse container starten*
```console
$ docker-compose up --build -d {container_name}
```
*Een superuser met aangepaste login-gegevens with custom credentials instellen (vul de  parameters naar voorkeur in voor jouw installatie)*
```console
$ docker exec -it nl-kat-coordination_rocky_1 python3 /app/rocky/manage.py setup \
  --username {admin_username} \
  --password {admin_password} \
  --email {admin_email}
```
By default a user named 'admin', with the password 'admin' should be available.

*Optionele seed van de database met OOI-informatie*
```console
$ docker exec -it nl-kat-coordination_rocky_1 python3 /app/rocky/manage.py loaddata OOI_database_seed.json
```
*octopoes-core installeren in je lokale python-omgeving met een symlink (na het klonen)*
```console
$ pip install -e nl-kat-coordination-octopoes-core
```

## 5. Updates
Een bestaande installatie updaten kan met het nieuwe make update. 

Ga naar de map waarin openkat staat:
```console
$ cd nl-kat-coordination
```

```console
$ make update
```

Vervolgens maak je een nieuwe superuser aan voor de nieuwe versie. De oude superuser kun je na de update verwijderen. Dit is niet mooi, maar heeft als voordeel dat je databases overeind blijven. Controleer of je overal op de meest recente versie zit, vooral Rocky blijft nog wel eens hangen ivm met yarn.lock. 

## 6. Hardening
Als je OpenKAT in een productieomgeving wilt gebruiken, gebruik dan de settings voor de hardening van de default setup: 

[Hardening settings](hardening_nl.adoc)

## 7. Tot slot
Wanneer de installatie voltooid is, kun je aan de slag met OpenKAT. Hiervoor kun je het beste beginnen bij de [Gebruikershandleiding OpenKAT](usermanual_nl.adoc).


