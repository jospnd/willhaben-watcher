# willhaben-watcher

Prüft in kurzen Abständen willhaben-Suchen auf neue Anzeigen und schickt dir eine Push-Nachricht aufs Handy. Läuft komplett kostenlos auf GitHub, dein PC muss dafür nicht an sein.

**So funktioniert es:** Ein kleines Python-Script (`watcher.py`) ruft deine willhaben-Suche ab, vergleicht sie mit den schon bekannten Anzeigen und meldet neue über [ntfy](https://ntfy.sh) aufs Handy. GitHub Actions führt das Script aus, und ein kostenloser Cron-Dienst stößt es regelmäßig an.

> **Wichtig:** Jeder richtet sich seine **eigene Kopie (Fork)** mit **eigenen Zugangsdaten** ein. Nutze niemals den Token oder Cronjob von jemand anderem.

## Was du brauchst

- einen kostenlosen [GitHub](https://github.com)-Account
- ein Smartphone mit der App **ntfy** (iOS / Android)
- einen kostenlosen Account bei [cron-job.org](https://cron-job.org)
- ca. 20 Minuten Zeit

## Einrichtung

### 1. ntfy-App einrichten

1. App **ntfy** installieren und Benachrichtigungen erlauben.
2. Auf **+** tippen und ein Topic mit einem **langen, zufälligen Namen** abonnieren, z. B. `willhaben-meinname-k7x2p9qw`. Server auf der Voreinstellung (`ntfy.sh`) lassen.
3. Den Namen genau aufschreiben. Er ist praktisch dein Passwort: Wer ihn kennt, kann deine Nachrichten mitlesen. Poste ihn nirgends öffentlich.

### 2. willhaben-Suche vorbereiten

1. Auf willhaben.at Kategorie und Filter einstellen (Preis, Ort, Zustand, Suchbegriff ...).
2. Die Sortierung auf **Neueste zuerst** stellen. Sonst stehen neue Anzeigen eventuell nicht unter den abgerufenen Treffern.
3. Die **komplette Adresse** aus der Adresszeile des Browsers kopieren und in einer Notiz zwischenspeichern.

### 3. Repo forken

1. Auf der Startseite dieses Repos oben rechts auf **Fork** klicken und mit **Create fork** bestätigen.
2. Lass den Fork **öffentlich**. Bei privaten Repos reicht das Gratis-Kontingent von GitHub nicht für häufige Läufe. Deine Links und Topics bleiben trotzdem geheim, weil sie im Secret liegen (Schritt 5).
3. Liegt in deinem Fork eine Datei `seen.json`, öffne sie und lösche sie (drei Punkte oben rechts → **Delete file** → **Commit changes**). Sie enthält nur den Stand des ursprünglichen Besitzers.

### 4. Actions aktivieren

1. In deinem Fork auf den Reiter **Actions**.
2. Den grünen Button **I understand my workflows, go ahead and enable them** klicken. In Forks sind Workflows zunächst ausgeschaltet.

### 5. Secret `SEARCHES` anlegen

1. In deinem Fork: **Settings** → links **Secrets and variables** → **Actions** → **New repository secret**.
2. Name: `SEARCHES` (genau so, Großbuchstaben).
3. Secret: eine Zeile in diesem Format, mit deinen eigenen Werten:

```json
[{"name":"suche1","url":"DEIN-WILLHABEN-LINK","topic":"DEIN-NTFY-TOPIC"}]
```

4. **Add secret** klicken.

Wichtig dabei:
- Es müssen **gerade Anführungszeichen** (`"`) sein. Bereite den Text nicht in Word oder einer Notizen-App vor, die daraus „typografische“ Zeichen macht.
- Beim `topic` steht nur der Name aus der ntfy-App, ohne `ntfy.sh` davor.

### 6. Erster Test

1. **Actions** → links **willhaben-watcher** wählen → rechts **Run workflow** → grüner Button **Run workflow**.
2. Nach ca. 30 Sekunden die Seite neu laden. Bei grünem Haken bekommst du am Handy die Nachricht *„Suchagent ‘suche1’ aktiv“*. Der Agent merkt sich dabei still alle bestehenden Anzeigen, ab dann kommen nur neue.
3. Roter Haken? Siehe Abschnitt [Fehlersuche](#fehlersuche).

### 7. Automatisch alle paar Minuten starten

GitHubs eingebauter Zeitplan ist oft stark verzögert. Deshalb stößt ein externer Cron-Dienst den Workflow regelmäßig an. Das richtest du **selbst** mit **deinem eigenen** Token ein.

**a) GitHub-Token erstellen**

1. GitHub: Profilbild oben rechts → **Settings** → ganz unten links **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Name z. B. `willhaben-trigger`, Ablauf **1 year**.
3. Bei **Repository access** **Only select repositories** wählen und **deinen Fork** auswählen.
4. Unter **Repository permissions** bei **Actions** auf **Read and write** stellen.
5. **Generate token** und den Token sofort kopieren (beginnt mit `github_pat_`). Er wird nur einmal angezeigt. Behandle ihn wie ein Passwort.

**b) Cronjob bei cron-job.org anlegen**

1. Bei [cron-job.org](https://cron-job.org) kostenlos registrieren, E-Mail bestätigen, dann **Create cronjob** (bzw. „Cronjob erstellen“).
2. **URL** (ersetze `DEIN-USERNAME` durch deinen GitHub-Namen und prüfe, dass dein Fork wirklich `willhaben-watcher` heißt):

```
https://api.github.com/repos/DEIN-USERNAME/willhaben-watcher/actions/workflows/watch.yml/dispatches
```

3. **Zeitplan:** alle 5 Minuten.
4. Reiter **Advanced** (bzw. „Erweitert“):
   - **Request method:** `POST`
   - Option **„Senden Sie JSON-Daten?“** aktivieren
   - **Headers** (Name links, Wert rechts):

| Name | Wert |
|---|---|
| `Authorization` | `Bearer DEIN-TOKEN` |
| `Accept` | `application/vnd.github+json` |
| `User-Agent` | `cronjob` |

   - Zwischen `Bearer` und deinem Token steht genau ein Leerzeichen.
   - **Request body:** `{"ref":"main"}`
5. Speichern und **Test run** klicken. Erfolg ist der Status **204 No Content**. Danach siehst du in deinem Fork unter **Actions** einen neuen Lauf mit „Manually run“.

| Status | Bedeutung |
|---|---|
| `401` | Token falsch oder unvollständig, oder das Leerzeichen nach `Bearer` fehlt |
| `404` | URL stimmt nicht (Username/Repo-Name) oder der Token hat keinen Zugriff auf deinen Fork |
| `422` | Der Request body `{"ref":"main"}` fehlt oder die Branch heißt nicht `main` |

## Mehrere Suchen, Filter und mehrere Empfänger

`SEARCHES` ist eine Liste. Jeder Eintrag ist ein eigener Suchagent:

```json
[
  {"name": "suche1", "url": "WILLHABEN-LINK-1", "topic": "NTFY-TOPIC"},
  {"name": "suche2", "url": "WILLHABEN-LINK-2", "topic": "NTFY-TOPIC", "max_price": 200, "exclude": ["defekt", "bastler"]}
]
```

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `name` | ja | eindeutiger Name des Agenten |
| `url` | ja | willhaben-Suchlink |
| `topic` | ja | ntfy-Topic, an das die Nachrichten gehen |
| `max_price` | nein | nur Anzeigen bis zu diesem Preis melden |
| `exclude` | nein | Anzeigen mit diesen Wörtern im Titel nicht melden |

- Zwischen den Einträgen steht ein Komma, nach dem letzten nicht.
- Jeder Eintrag braucht einen **eigenen `name`**.
- Das Secret ersetzt beim Bearbeiten **immer den kompletten alten Inhalt** (GitHub zeigt den alten Text nicht an). Kopiere dir deinen aktuellen Text deshalb vorher in eine Notiz und ergänze dort.
- Neue Agenten starten beim nächsten Lauf automatisch still und melden sich mit „Suchagent ‘…’ aktiv“. Du wirst nicht mit alten Anzeigen geflutet.
- Pro Lauf und Agent kommen maximal 8 Einzelnachrichten, damit dein Handy nicht überflutet wird.

## Fehlersuche

**Lauf ist rot:** In **Actions** auf den roten Lauf klicken → links auf **check** → den Schritt **Run watcher** aufklappen. Die letzte Zeile nennt meist den Grund:

| Meldung | Ursache |
|---|---|
| `Konfigurationsfehler: ...` oder `Keine Suchagenten konfiguriert` | Das Secret `SEARCHES` fehlt, heißt anders oder enthält ungültiges JSON (fehlendes Komma, fehlende Klammer, nicht gerade Anführungszeichen) |
| `__NEXT_DATA__ nicht gefunden` | willhaben hat die Seitenstruktur geändert oder blockt Anfragen |
| `403` / `429` | willhaben blockt zu häufige Anfragen. Intervall auf 5 bis 10 Minuten erhöhen |

Die gelben Hinweise zu Node.js und Ubuntu in den Lauf-Annotationen sind harmlos.

**Keine Nachrichten am Handy:** Stimmt das `topic` im Secret **exakt** (Groß-/Kleinschreibung, Bindestriche) mit dem Topic in der ntfy-App überein? Sind Benachrichtigungen für die App erlaubt?

**Läufe starten nicht mehr:** Der GitHub-Token läuft nach einem Jahr ab. Dann liefert der Cronjob `401`. Neuen Token erstellen und im Header bei cron-job.org austauschen. In cron-job.org kannst du auch eine E-Mail bei Fehlschlägen aktivieren.

## Hinweise

- Das Script liest die öffentlichen Suchergebnisseiten von willhaben. Es gibt keine offizielle API, und die Seitenstruktur kann sich jederzeit ändern.
- Das Projekt ist für den privaten Gebrauch mit moderater Frequenz gedacht. Empfohlen sind 5 Minuten, nicht weniger als 2. Prüfe selbst, ob das mit den Nutzungsbedingungen von willhaben und GitHub für dich in Ordnung ist. Die Nutzung erfolgt auf eigene Verantwortung.
- Dein `SEARCHES`-Secret, dein GitHub-Token und dein ntfy-Topic gehören **nie** in eine Datei im Repo oder in ein Issue.

## Dateien im Repo

| Datei | Zweck |
|---|---|
| `watcher.py` | das Script: Suche abrufen, neue Anzeigen erkennen, Push senden |
| `.github/workflows/watch.yml` | GitHub-Actions-Workflow, der das Script ausführt |
| `seen.json` | automatisch gepflegt: merkt sich pro Agent die schon gesehenen Anzeigen |
