# Home Assistant NAD Receiver Integration - Deutsche Dokumentation

## 📋 Übersicht

Dies ist eine **Home Assistant Integration für NAD Receiver**, die es ermöglicht, NAD-Audiogeräte über die serielle Schnittstelle (RS-232), Telnet oder TCP zu steuern. Die Integration bietet eine umfassende Steuerung von NAD-Receivern und ermöglicht die Integration in Home Assistant Automatisierungen.

---

## 🏗️ Architekturübersicht

### Hauptkomponenten

```
custom_components/nad/
├── __init__.py          # Hauptintegrations-Setup und Coordinator
├── const.py             # Konstanten und Konfiguration
├── config_flow.py       # Konfigurations-Assistent (UI)
├── manifest.json        # Integration-Metadaten
├── media_player.py      # Media Player Entitäten (Hauptzone, Zone 2)
├── switch.py            # Schalter-Entitäten (z.B. Lautsprecher, Ton-Optionen)
├── number.py            # Zahlen-Entitäten (z.B. Lautstärke, Abstände, Frequenzen)
├── select.py            # Auswahl-Entitäten (z.B. Klangmodi, Lautsprecherkonfiguration)
└── sensor.py            # Sensor-Entitäten (z.B. Tuner-Informationen)
```

---

## 📦 Abhängigkeiten

Die Integration benötigt die externe Python-Bibliothek **`nad_receiver`** (Version 0.3.0), die die eigentliche Kommunikation mit den NAD-Geräten über verschiedene Protokolle handhabt:

- **RS-232 (Seriell)**: Direkte Verbindung über serielle Schnittstelle
- **Telnet**: Netzwerkverbindung über Telnet-Protokoll
- **TCP**: Direkte TCP-Verbindung

---

## 🔧 Installation

### Option 1: Über HACS (Empfohlen)

1. Gehen Sie zu **HACS** → **Integrationen**
2. Öffnen Sie das Menü **Benutzerdefinierte Repositorys**
3. Fügen Sie die Repository-URL hinzu: `https://github.com/rrooggiieerr/homeassistant-nad`
4. Wählen Sie **Integration** als Kategorie
5. Klicken Sie auf **Hinzufügen**
6. Suchen Sie nach "NAD" und installieren Sie die Integration
7. Starten Sie Home Assistant neu

### Option 2: Manuell

1. Kopieren Sie das Verzeichnis `custom_components/nad` aus diesem Repository
2. Fügen Sie es in Ihr Home Assistant Verzeichnis unter `config/custom_components/` ein
3. Starten Sie Home Assistant neu

---

## ⚙️ Konfiguration

### Schritt-für-Schritt Anleitung

1. **Nach dem Neustart**: Gehen Sie zu **Einstellungen** → **Geräte & Dienste**
2. Klicken Sie auf **+ Integration hinzufügen**
3. Suchen Sie nach **"NAD"** und wählen Sie die Integration aus
4. Wählen Sie die Verbindungstyp aus:
   - **RS232 (Seriell)**: Für direkte serielle Verbindung
   - **Telnet**: Für Netzwerkverbindung über Telnet
   - **TCP**: Für direkte TCP-Verbindung

### Verbindungstypen im Detail

#### 1. Seriell (RS-232)
- **Verfügbare Ports**: Werden automatisch erkannt und angezeigt
- **Manuelle Eingabe**: Möglich, falls der Port nicht automatisch erkannt wird
- **Beispiel**: `/dev/ttyUSB0` oder `/dev/serial/by-id/...`

#### 2. Telnet
- **Host**: IP-Adresse oder Hostname des NAD-Geräts oder esp-link
- **Port**: Standardmäßig Port 53 (kann angepasst werden)

#### 3. TCP
- **Host**: IP-Adresse oder Hostname des NAD-Geräts

---

## 🎯 Entitäten

Die Integration erstellt verschiedene Entitäten basierend auf den Fähigkeiten Ihres NAD-Receivers. Alle Entitäten werden automatisch erkannt und nur die unterstützten Funktionen werden angezeigt.

### 1. Media Player (`media_player.nad_*`)

**Hauptzone (Main Zone):**
- **Funktionen:**
  - Ein/Aus schalten
  - Lautstärke regeln (absolut und relativ)
  - Stummschaltung
  - Quelle auswählen
  - Klangmodus auswählen (z.B. Dolby ProLogic, NEO:6, etc.)

**Zone 2:**
- **Funktionen:**
  - Ein/Aus schalten
  - Lautstärke regeln
  - Stummschaltung
  - Quelle auswählen

**Unterstützte Klangmodi:**
- None
- ProLogic
- PLIIMovie
- PLIIMusic
- NEO6Cinema
- NEO6Music
- EARS
- EnhancedStereo
- AnalogBypass
- StereoDownmix
- SurroundEX

### 2. Schalter (`switch.nad_*`)

Die Integration erstellt Schalter für verschiedene Funktionen:

**Lautsprecher:**
- `switch.nad_speaker_sub` - Subwoofer ein/aus
- `switch.nad_speaker_a` - Lautsprecher A ein/aus
- `switch.nad_speaker_b` - Lautsprecher B ein/aus

**Ton-Optionen:**
- `switch.nad_main_tone_defeat` - Tone Defeat (Ton-Korrektur deaktivieren)
- `switch.nad_main_enhanced_bass` - Verbesserten Bass aktivieren

**Dolby-Funktionen:**
- `switch.nad_main_dolby_panorama` - Dolby Panorama

**Anzeige:**
- `switch.nad_main_vfd_dimmer` - Front VFD Display Dimmer
- `switch.nad_main_osd_temp_display` - OSD Temperaturanzeige

**Enhanced Stereo:**
- `switch.nad_main_enhanced_stereo_back` - Enhanced Stereo Rückseite
- `switch.nad_main_enhanced_stereo_center` - Enhanced Stereo Mitte
- `switch.nad_main_enhanced_stereo_front` - Enhanced Stereo Front
- `switch.nad_main_enhanced_stereo_surround` - Enhanced Stereo Surround

**Tuner:**
- `switch.nad_tuner_fm_mute` - FM-Tuner Stummschaltung

### 3. Zahlen-Entitäten (`number.nad_*`)

**Ton-Kontrollen:**
- `number.nad_main_bass` - Bass-Regler (-10 bis +10 dB)
- `number.nad_main_treble` - Höhen-Regler (-10 bis +10 dB)

**Lautsprecher-Pegel:**
- `number.nad_main_level_center` - Center-Lautstärke (-12 bis +12 dB)
- `number.nad_main_level_left` - Linker Lautsprecher (-12 bis +12 dB)
- `number.nad_main_level_right` - Rechter Lautsprecher (-12 bis +12 dB)
- `number.nad_main_level_sub` - Subwoofer-Lautstärke (-12 bis +12 dB)
- `number.nad_main_level_surround_left` - Surround Links (-12 bis +12 dB)
- `number.nad_main_level_surround_right` - Surround Rechts (-12 bis +12 dB)
- `number.nad_main_level_back_left` - Rückseite Links (-12 bis +12 dB)
- `number.nad_main_level_back_right` - Rückseite Rechts (-12 bis +12 dB)

**Trim-Regler:**
- `number.nad_main_trim_center` - Center-Trim (-6 bis +6)
- `number.nad_main_trim_sub` - Subwoofer-Trim (-6 bis +6)
- `number.nad_main_trim_surround` - Surround-Trim (-6 bis +6)

**Lautsprecher-Abstände:**
- `number.nad_main_distance_center` - Abstand Center (0-30 Fuß)
- `number.nad_main_distance_left` - Abstand Links (0-30 Fuß)
- `number.nad_main_distance_right` - Abstand Rechts (0-30 Fuß)
- `number.nad_main_distance_sub` - Abstand Subwoofer (0-30 Fuß)
- `number.nad_main_distance_surround_left` - Abstand Surround Links (0-30 Fuß)
- `number.nad_main_distance_surround_right` - Abstand Surround Rechts (0-30 Fuß)
- `number.nad_main_distance_back_left` - Abstand Rückseite Links (0-30 Fuß)
- `number.nad_main_distance_back_right` - Abstand Rückseite Rechts (0-30 Fuß)

**Lautsprecher-Crossover-Frequenzen:**
- `number.nad_main_speaker_back_frequency` - Crossover Rückseite (40-200 Hz)
- `number.nad_main_speaker_center_frequency` - Crossover Center (40-200 Hz)
- `number.nad_main_speaker_front_frequency` - Crossover Front (40-200 Hz)
- `number.nad_main_speaker_surround_frequency` - Crossover Surround (40-200 Hz)

**Dolby-Einstellungen:**
- `number.nad_main_dolby_center_width` - Dolby Center-Breite (0-7)
- `number.nad_main_dolby_dimension` - Dolby Dimension (-7 bis +7)
- `number.nad_main_dolby_drc` - Dolby Dynamic Range Control (25-100%)

**DTS-Einstellungen:**
- `number.nad_main_dts_center_gain` - DTS Center-Verstärkung (0-0.5)
- `number.nad_main_dts_drc` - DTS Dynamic Range Control (25-100%)

**LipSync & Trigger:**
- `number.nad_main_lip_sync_delay` - LipSync-Verzögerung (0-120 ms)
- `number.nad_main_trigger1_delay` - Trigger 1 Verzögerung (0-15 s)
- `number.nad_main_trigger2_delay` - Trigger 2 Verzögerung (0-15 s)
- `number.nad_main_trigger3_delay` - Trigger 3 Verzögerung (0-15 s)

**Tuner:**
- `number.nad_tuner_am_frequency` - AM-Frequenz (530-1710 kHz)
- `number.nad_tuner_fm_frequency` - FM-Frequenz (87.5-108.5 MHz)
- `number.nad_tuner_preset` - Tuner-Vorwahl (1-40)
- `number.nad_tuner_xm_channel` - XM-Kanal (0-255)

### 4. Auswahl-Entitäten (`select.nad_*`)

**Klangmodi:**
- `select.nad_main_listening_mode_analog` - Analog-Signal-Klangmodus
- `select.nad_main_listening_mode_digital` - Digital-Signal-Klangmodus
- `select.nad_main_listening_mode_dolby_digital` - Dolby Digital Klangmodus
- `select.nad_main_listening_mode_dolby_digital_2ch` - Dolby Digital 2-Kanal Klangmodus
- `select.nad_main_listening_mode_dts` - DTS Klangmodus

**Lautsprecher-Konfiguration:**
- `select.nad_main_speaker_back_config2` - Lautsprechergröße Rückseite (Small/Large)
- `select.nad_main_speaker_center_config` - Lautsprechergröße Center (Off/Small/Large)
- `select.nad_main_speaker_front_config` - Lautsprechergröße Front (Small/Large)
- `select.nad_main_speaker_surround_config` - Lautsprechergröße Surround (Off/Small/Large)

**Trigger:**
- `select.nad_main_auto_trigger` - Trigger-Eingang (Main/Zone2/Zone3/Zone4/All)
- `select.nad_main_trigger1_out` - Trigger 1 Ausgang
- `select.nad_main_trigger2_out` - Trigger 2 Ausgang
- `select.nad_main_trigger3_out` - Trigger 3 Ausgang

**Anzeige:**
- `select.nad_main_vfd_display` - VFD-Anzeige (On/Temp)
- `select.nad_main_vfd_line1` - VFD Zeile 1
- `select.nad_main_vfd_line2` - VFD Zeile 2
- `select.nad_main_vfd_templine` - VFD Temperaturzeile (1/2)

**Video & Tuner:**
- `select.nad_main_video_mode` - Videomodus (NTSC/PAL)
- `select.nad_tuner_band` - Tuner-Band (AM/FM/XM/DAB)
- `select.nad_tuner_digital_mode` - Tuner-Digitalmodus (XM/DAB)

### 5. Sensoren (`sensor.nad_*`)

**System-Informationen:**
- `sensor.nad_dsp_version` - DSP-Version
- `sensor.nad_uart_version` - UART-Version

**Tuner-Informationen:**
- `sensor.nad_tuner_dab_dls` - DAB DLS-Text
- `sensor.nad_tuner_dab_service` - DAB Service-Name
- `sensor.nad_tuner_fm_rdsname` - FM RDS Stationname
- `sensor.nad_tuner_fm_rdstext` - FM RDS Text
- `sensor.nad_tuner_xm_channel_name` - XM Kanalname
- `sensor.nad_tuner_xm_name` - XM Name
- `sensor.nad_tuner_xm_title` - XM Titel

---

## 🔄 Datenfluss und Kommunikation

### 1. NADReceiverCoordinator

Der **NADReceiverCoordinator** ist das Herzstück der Integration und verantwortlich für:

- **Verbindungsverwaltung**: Herstellung und Verwaltung der Verbindung zum NAD-Gerät
- **Datenabruf**: Regelmäßiges Abfragen des Gerätestatus (alle 5 Sekunden)
- **Befehlsausführung**: Senden von Befehlen an das Gerät
- **Daten-Caching**: Zwischenspeicherung der Geräteinformationen
- **Listener-Verwaltung**: Verwaltung von Entitäten, die Datenbenachrichtigungen erhalten

**Wichtige Methoden:**

```python
# Verbindung herstellen
async def connect(self) -> bool:
    # Holt Modell und Version
    self.model = self.exec_command("Main.Model", "?")
    self.version = self.exec_command("Main.Version", "?")
    # Erstellt DeviceInfo für Home Assistant

# Befehl ausführen
def exec_command(self, command: str, operator: str, value: Optional = None):
    # Sendet Befehl an das Gerät und empfängt Antwort
    # Format: "Befehl?" für Abfrage, "Befehl=Wert" für Setzen

# Unterstützte Befehle prüfen
def supports_command(self, command: str):
    # Prüft ob ein Befehl vom Gerät unterstützt wird
```

### 2. Befehlsformat

Die Kommunikation mit NAD-Geräten erfolgt über ein einfaches Textprotokoll:

- **Abfrage**: `Befehl?` → Antwort: `Befehl=Wert` oder leer (nicht unterstützt)
- **Setzen**: `Befehl=Wert` → Antwort: `Befehl=Wert` oder Fehler

**Beispiele:**
- `Main.Power?` → `Main.Power=On` oder `Main.Power=Off`
- `Main.Volume?` → `Main.Volume=-30` (Lautstärke in dB)
- `Main.Source?` → `Main.Source=3` (Quellen-Nummer)
- `Main.Power=On` → `Main.Power=On` (Bestätigung)
- `Main.Volume=-25` → `Main.Volume=-25` (neue Lautstärke)

### 3. Daten-Update-Zyklus

1. **Coordinator** fragt alle 5 Sekunden den Status ab
2. **Power-Status** wird immer abgefragt
3. **Listener-Befehle** werden für alle registrierten Entitäten abgefragt
4. **Entitäten** erhalten Updates und aktualisieren ihren Zustand

---

## 🎛️ Media Player Implementierung

### Hauptklasse: `NAD` (Basisklasse)

Die Basisklasse für alle Media Player Entitäten bietet:

**Eigenschaften:**
- `_attr_has_entity_name = True` - Verwendet Entity-Namen aus der Konfiguration
- `_attr_device_class = MediaPlayerDeviceClass.RECEIVER` - Geräteklasse
- `zone = "Main"` oder `"Zone2"` - Zone des Receivers

**Unterstützte Funktionen:**
- `turn_on()` / `turn_off()` - Ein/Aus schalten
- `volume_up()` / `volume_down()` - Lautstärke relativ ändern
- `set_volume_level(volume)` - Lautstärke absolut setzen (0.0-1.0)
- `mute_volume(mute)` - Stummschaltung
- `select_source(source)` - Quelle auswählen

**Volumen-Berechnung:**
```python
def calc_volume(self, decibel):
    # Konvertiert dB in 0.0-1.0 Bereich
    # Standard: -92dB (Min) bis -20dB (Max)
    return abs(self._min_volume - decibel) / abs(self._min_volume - self._max_volume)

def calc_db(self, volume):
    # Konvertiert 0.0-1.0 in dB
    return self._min_volume + round(abs(self._min_volume - self._max_volume) * volume)
```

### Spezialisierte Klassen

**`NADMain`** - Hauptzone mit zusätzlichen Funktionen:
- Klangmodus-Auswahl (`select_sound_mode`)
- Unterstützt alle Media Player Funktionen

**`NADZone2`** - Zone 2:
- Grundlegende Media Player Funktionen
- Keine Klangmodus-Auswahl

---

## 🔌 Konfigurations-Assistent (Config Flow)

### Schritt 1: Verbindungstyp auswählen

Der Benutzer wählt zwischen:
- `setup_serial` - Serielle Verbindung
- `setup_telnet` - Telnet-Verbindung
- `setup_tcp` - TCP-Verbindung

### Schritt 2: Verbindung konfigurieren

**Seriell:**
- Verfügbare Ports werden automatisch erkannt
- Manuelle Eingabe möglich
- Validierung der Port-Existenz

**Telnet/TCP:**
- Host und Port eingeben
- Verbindungstest
- Modellabfrage

### Schritt 3: Validierung

1. Verbindung wird getestet
2. Modell wird abgefragt (`Main.Model?`)
3. Version wird abgefragt (`Main.Version?`)
4. Bei Erfolg: Integration wird erstellt

### Options Flow (Einstellungen)

Nach der Erstellung können folgende Optionen angepasst werden:
- `min_volume` - Minimale Lautstärke in dB (Standard: -92)
- `max_volume` - Maximale Lautstärke in dB (Standard: -20)
- `volume_step` - Lautstärkeschritt (Standard: 4)

---

## 📊 Entitäts-Erkennung

### Dynamische Entitäts-Erstellung

Die Integration erstellt Entitäten **dynamisch** basierend auf den Fähigkeiten des Geräts:

1. **Coordinator** prüft mit `supports_command()` ob ein Befehl unterstützt wird
2. Nur unterstützte Befehle werden als Entitäten erstellt
3. Dies stellt sicher, dass nur verfügbare Funktionen angezeigt werden

**Beispiel aus `switch.py`:**
```python
entity_descriptions = [
    SwitchEntityDescription(key="Main.Dimmer", name="Front VFD Dimmer", ...),
    SwitchEntityDescription(key="Main.Speaker.Sub", name="Subwoofer", ...),
    # ... weitere Beschreibungen
]

entities = []
for entity_description in entity_descriptions:
    if coordinator.supports_command(entity_description.key):
        entities.append(NADReceiverSwitch(coordinator, entity_description))

async_add_entities(entities)
```

### Entity Categories

Viele Entitäten verwenden **EntityCategory.CONFIG**, was bedeutet:
- Sie werden standardmäßig ausgeblendet
- Müssen manuell in den Einstellungen aktiviert werden
- Sind für erweiterte Konfiguration gedacht

---

## 🔧 Technische Details

### Abhängigkeiten

```json
{
  "requirements": ["nad_receiver==0.3.0"]
}
```

Die `nad_receiver`-Bibliothek bietet:
- `NADReceiver` - Für serielle Verbindung
- `NADReceiverTCP` - Für TCP-Verbindung
- `NADReceiverTelnet` - Für Telnet-Verbindung

### Logger

Die Integration verwendet folgende Logger:
- `nad_receiver` - Für Bibliotheks-Logs
- `__name__` (custom_components.nad) - Für Integrations-Logs

### Fehlerbehandlung

**Häufige Fehler:**
- `ConfigEntryNotReady` - Verbindung konnte nicht hergestellt werden
- `CommandNotSupportedError` - Befehl wird vom Gerät nicht unterstützt
- `serial.SerialException` - Serielle Verbindungsfehler
- `IOError` - Allgemeine Ein-/Ausgabefehler

### Migration

Die Integration unterstützt die Migration von alten Unique IDs:
```python
async def _async_migrate_entity_entry(self, registry_entry):
    # Migriert von Port-basierten IDs zu Config Entry-basierten IDs
    if registry_entry.unique_id.startswith(f"{entry.data[CONF_SERIAL_PORT]}-"):
        new_unique_id = registry_entry.unique_id.replace(
            f"{entry.data[CONF_SERIAL_PORT]}-",
            f"{registry_entry.config_entry_id}-",
        )
        return {"new_unique_id": new_unique_id}
```

---

## 📝 YAML-Konfiguration (veraltet)

**Hinweis:** Diese Integration verwendet **nur** die Config Flow UI. Eine manuelle YAML-Konfiguration ist nicht möglich.

---

## 🎯 Automatisierungsbeispiele

### Beispiel 1: Lautstärke anpassen bei bestimmten Bedingungen

```yaml
automation:
  - alias: "Lautstärke reduzieren wenn niemand zu Hause"
    trigger:
      - platform: state
        entity_id: group.all_persons
        to: "not_home"
    action:
      - service: media_player.volume_set
        target:
          entity_id: media_player.nad_main
        data:
          volume_level: 0.3
```

### Beispiel 2: Quelle wechseln bei Bewegung

```yaml
automation:
  - alias: "Schalte auf TV wenn Bewegung erkannt"
    trigger:
      - platform: state
        entity_id: binary_sensor.living_room_motion
        to: "on"
    condition:
      - condition: state
        entity_id: media_player.nad_main
        state: "off"
    action:
      - service: media_player.turn_on
        target:
          entity_id: media_player.nad_main
      - service: media_player.select_source
        target:
          entity_id: media_player.nad_main
        data:
          source: "TV"
```

### Beispiel 3: Klangmodus basierend auf Inhalt

```yaml
automation:
  - alias: "Film-Modus für Netflix"
    trigger:
      - platform: state
        entity_id: media_player.tv
        to: "Netflix"
    action:
      - service: select.select_option
        target:
          entity_id: select.nad_main_listening_mode_digital
        data:
          option: "PLIIMovie"
```

### Beispiel 4: Subwoofer bei Nacht ausschalten

```yaml
automation:
  - alias: "Subwoofer nachts ausschalten"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.nad_speaker_sub

  - alias: "Subwoofer morgens einschalten"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.nad_speaker_sub
```

---

## 🛠️ Fehlerbehebung

### Häufige Probleme

#### 1. Verbindung kann nicht hergestellt werden

**Ursachen:**
- Falscher serieller Port
- Falsche IP-Adresse oder Port
- Gerät ist ausgeschaltet
- Falsches Kabel oder Verbindung

**Lösungen:**
- Prüfen Sie die Verbindung mit einem Terminal-Programm
- Testen Sie die serielle Verbindung mit `screen` oder `minicom`
- Für Netzwerk: Prüfen Sie mit `telnet <IP> <Port>` oder `nc -zv <IP> <Port>`

#### 2. Befehle werden nicht unterstützt

**Ursachen:**
- Älteres NAD-Modell mit begrenzter Befehlsunterstützung
- Falsche Firmware-Version

**Lösungen:**
- Prüfen Sie die unterstützten Befehle mit der NAD-Remote oder Dokumentation
- Die Integration zeigt nur unterstützte Entitäten an

#### 3. Lautstärke funktioniert nicht

**Ursachen:**
- Falsche Min/Max-Werte in den Optionen
- Gerät unterstützt keine absolute Lautstärke-Einstellung

**Lösungen:**
- Passen Sie `min_volume` und `max_volume` in den Integrationseinstellungen an
- Verwenden Sie `volume_up`/`volume_down` statt `set_volume_level`

#### 4. Entitäten werden nicht angezeigt

**Ursachen:**
- Entitäten sind deaktiviert (EntityCategory.CONFIG)
- Gerät unterstützt die Funktion nicht

**Lösungen:**
- Gehen Sie zu **Einstellungen** → **Geräte & Dienste** → **Entitäten**
- Aktivieren Sie die gewünschten Entitäten

### Debug-Logging aktivieren

Fügen Sie folgende Zeilen zu Ihrer `configuration.yaml` hinzu:

```yaml
logger:
  default: info
  logs:
    custom_components.nad: debug
    nad_receiver: debug
```

Dann starten Sie Home Assistant neu und prüfen Sie die Logs.

---

## 📚 Unterstützte NAD-Modelle

Die Integration sollte mit den meisten **NAD-Receivern** funktionieren, die das **RS-232-Protokoll** oder **Netzwerksteuerung** unterstützen, darunter:

- NAD T 758
- NAD T 777
- NAD T 787
- NAD C 356
- NAD C 375
- NAD C 388
- NAD C 390
- NAD M17
- Und viele weitere...

**Hinweis:** Nicht alle Modelle unterstützen alle Befehle. Die Integration passt sich automatisch an die Fähigkeiten Ihres Geräts an.

---

## 🔄 Aktualisierung

### Über HACS

1. Gehen Sie zu **HACS** → **Integrationen**
2. Suchen Sie nach "NAD"
3. Klicken Sie auf **Aktualisieren**
4. Starten Sie Home Assistant neu

### Manuell

1. Laden Sie die neueste Version herunter
2. Ersetzen Sie das `custom_components/nad` Verzeichnis
3. Starten Sie Home Assistant neu

---

## 🤝 Beitrag leisten

### Übersetzungen

Die Integration unterstützt Übersetzungen. Um eine neue Sprache hinzuzufügen:

1. Erstellen Sie eine Datei `strings.json` im Verzeichnis `custom_components/nad/translations/<sprache>`
2. Übersetzen Sie alle Strings aus der englischen `strings.json`
3. Erstellen Sie einen Pull Request

### Fehler melden

1. Gehen Sie zu [GitHub Issues](https://github.com/rrooggiieerr/homeassistant-nad/issues)
2. Prüfen Sie, ob das Problem bereits gemeldet wurde
3. Erstellen Sie einen neuen Issue mit:
   - Home Assistant Version
   - NAD-Modell
   - Verbindungstyp (Seriell/Telnet/TCP)
   - Fehlerbeschreibung
   - Log-Ausschnitte (mit Debug-Logging)

### Code-Beiträge

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch
3. Commiten Sie Ihre Änderungen
4. Pushen Sie zum Branch
5. Erstellen Sie einen Pull Request

---

## 📄 Lizenz

Diese Integration steht unter der **MIT-Lizenz**. Siehe [LICENSE](LICENSE) für Details.

---

## 🙏 Dank

- **@rrooggiieerr** - Hauptentwickler
- Alle Beitragenden und Tester
- Die Home Assistant Community

---

## 📞 Support

Für Fragen und Unterstützung:

1. **GitHub Discussions**: [Discussions](https://github.com/rrooggiieerr/homeassistant-nad/discussions)
2. **Home Assistant Community Forum**: [Forum](https://community.home-assistant.io/)
3. **Sponsoring**: Siehe [README.md](README.md) für Sponsoring-Optionen

---

*Diese Dokumentation wurde für die deutsche Home Assistant Community erstellt. Letzte Aktualisierung: 2024*
