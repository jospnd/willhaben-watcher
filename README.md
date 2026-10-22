# willhaben-watcher

Prüft alle ca. 5 Minuten willhaben-Suchen auf neue Anzeigen und schickt eine Push-Nachricht via ntfy.

## Einrichten

1. ntfy-App installieren und ein Topic mit langem, zufälligem Namen abonnieren.
2. Suche auf willhaben einstellen, nach "Neueste zuerst" sortieren, Link kopieren.
3. Im Repo unter Settings → Secrets and variables → Actions ein Secret `SEARCHES` anlegen.

## Format von SEARCHES

Eine JSON-Liste in einer Zeile, gerade Anführungszeichen (") verwenden:

```json
[
  {"name": "suche1", "url": "WILLHABEN-LINK", "topic": "NTFY-TOPIC"},
  {"name": "suche2", "url": "WILLHABEN-LINK", "topic": "NTFY-TOPIC", "max_price": 200, "exclude": ["defekt", "bastler"]}
]
```

- `name`: eindeutig pro Suche (Pflicht)
- `url`: willhaben-Suchlink (Pflicht)
- `topic`: ntfy-Topic, an das die Nachrichten gehen (Pflicht)
- `max_price`: nur Anzeigen bis zu diesem Preis melden (optional)
- `exclude`: Anzeigen mit diesen Wörtern im Titel nicht melden (optional)

Zwischen den Einträgen steht ein Komma, nach dem letzten nicht.
