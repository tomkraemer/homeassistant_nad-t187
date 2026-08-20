# NAD Receiver Integration - Quick Reference (Schnellübersicht)

## 📌 Wichtigste Informationen auf einen Blick

---

## 🎯 Installation

### Über HACS (Empfohlen)
```
1. HACS → Integrationen → Benutzerdefinierte Repositorys
2. URL: https://github.com/rrooggiieerr/homeassistant-nad
3. Kategorie: Integration
4. Hinzufügen → NAD suchen → Installieren
5. Home Assistant neu starten
```

### Manuell
```bash
# Kopieren Sie das Verzeichnis
cp -r /pfad/zur/integration/custom_components/nad \
   /config/custom_components/

# Home Assistant neu starten
```

---

## ⚙️ Konfiguration

### Verbindungstypen
| Typ | Parameter | Standard-Port | Beschreibung |
|-----|-----------|---------------|--------------|
| **RS-232** | Serieller Port | - | Direkte serielle Verbindung |
| **Telnet** | Host, Port | 53 | Netzwerk über Telnet |
| **TCP** | Host | - | Direkte TCP-Verbindung |

### Setup-Schritte
1. **Einstellungen** → **Geräte & Dienste** → **+ Integration hinzufügen**
2. **"NAD"** suchen und auswählen
3. **Verbindungstyp** auswählen (RS-232, Telnet, TCP)
4. **Verbindungsparameter** eingeben
5. **Fertigstellen**

---

## 🎛️ Entitäten Übersicht

### Media Player (Hauptsteuerung)

| Entität | Beschreibung | Unterstützte Funktionen |
|---------|--------------|------------------------|
| `media_player.nad_main` | Hauptzone | Ein/Aus, Lautstärke, Stummschaltung, Quelle, Klangmodus |
| `media_player.nad_zone_2` | Zone 2 | Ein/Aus, Lautstärke, Stummschaltung, Quelle |

**Klangmodi:**
- None, ProLogic, PLIIMovie, PLIIMusic, NEO6Cinema, NEO6Music, EARS
- EnhancedStereo, AnalogBypass, StereoDownmix, SurroundEX

---

### Schalter (Switches)

#### Lautsprecher
| Entität | Beschreibung |
|---------|--------------|
| `switch.nad_speaker_sub` | Subwoofer ein/aus |
| `switch.nad_speaker_a` | Lautsprecher A ein/aus |
| `switch.nad_speaker_b` | Lautsprecher B ein/aus |

#### Ton-Optionen
| Entität | Beschreibung |
|---------|--------------|
| `switch.nad_main_tone_defeat` | Tone Defeat (Ton-Korrektur deaktivieren) |
| `switch.nad_main_enhanced_bass` | Verbesserten Bass aktivieren |
| `switch.nad_main_dolby_panorama` | Dolby Panorama |

#### Enhanced Stereo
| Entität | Beschreibung |
|---------|--------------|
| `switch.nad_main_enhanced_stereo_back` | Enhanced Stereo Rückseite |
| `switch.nad_main_enhanced_stereo_center` | Enhanced Stereo Mitte |
| `switch.nad_main_enhanced_stereo_front` | Enhanced Stereo Front |
| `switch.nad_main_enhanced_stereo_surround` | Enhanced Stereo Surround |

#### Anzeige
| Entität | Beschreibung |
|---------|--------------|
| `switch.nad_main_vfd_dimmer` | Front VFD Display Dimmer |
| `switch.nad_main_osd_temp_display` | OSD Temperaturanzeige |

#### Tuner
| Entität | Beschreibung |
|---------|--------------|
| `switch.nad_tuner_fm_mute` | FM-Tuner Stummschaltung |

---

### Zahlen-Entitäten (Number)

#### Ton-Kontrollen
| Entität | Bereich | Einheit | Beschreibung |
|---------|---------|--------|--------------|
| `number.nad_main_bass` | -10 bis +10 | dB | Bass-Regler |
| `number.nad_main_treble` | -10 bis +10 | Hz | Höhen-Regler |

#### Lautsprecher-Pegel
| Entität | Bereich | Einheit | Beschreibung |
|---------|---------|--------|--------------|
| `number.nad_main_level_center` | -12 bis +12 | dB | Center-Lautstärke |
| `number.nad_main_level_left` | -12 bis +12 | dB | Linker Lautsprecher |
| `number.nad_main_level_right` | -12 bis +12 | dB | Rechter Lautsprecher |
| `number.nad_main_level_sub` | -12 bis +12 | dB | Subwoofer-Lautstärke |
| `number.nad_main_level_surround_left` | -12 bis +12 | dB | Surround Links |
| `number.nad_main_level_surround_right` | -12 bis +12 | dB | Surround Rechts |
| `number.nad_main_level_back_left` | -12 bis +12 | dB | Rückseite Links |
| `number.nad_main_level_back_right` | -12 bis +12 | dB | Rückseite Rechts |

#### Trim-Regler
| Entität | Bereich | Beschreibung |
|---------|---------|--------------|
| `number.nad_main_trim_center` | -6 bis +6 | Center-Trim |
| `number.nad_main_trim_sub` | -6 bis +6 | Subwoofer-Trim |
| `number.nad_main_trim_surround` | -6 bis +6 | Surround-Trim |

#### Lautsprecher-Abstände
| Entität | Bereich | Einheit | Beschreibung |
|---------|---------|--------|--------------|
| `number.nad_main_distance_*` | 0 bis 30 | Fuß | Abstand für verschiedene Lautsprecher |

#### Crossover-Frequenzen
| Entität | Bereich | Einheit | Beschreibung |
|---------|---------|--------|--------------|
| `number.nad_main_speaker_*_frequency` | 40 bis 200 | Hz | Crossover für verschiedene Lautsprecher |

#### Dolby-Einstellungen
| Entität | Bereich | Einheit | Beschreibung |
|---------|---------|--------|--------------|
| `number.nad_main_dolby_center_width` | 0 bis 7 | - | Dolby Center-Breite |
| `number.nad_main_dolby_dimension` | -7 bis +7 | - | Dolby Dimension |
| `number.nad_main_dolby_drc` | 25 bis 100 | % | Dolby Dynamic Range Control |

#### DTS-Einstellungen
| Entität | Bereich | Einheit | Beschreibung |
|---------|---------|--------|--------------|
| `number.nad_main_dts_center_gain` | 0 bis 0.5 | - | DTS Center-Verstärkung |
| `number.nad_main_dts_drc` | 25 bis 100 | % | DTS Dynamic Range Control |

#### LipSync & Trigger
| Entität | Bereich | Einheit | Beschreibung |
|---------|---------|--------|--------------|
| `number.nad_main_lip_sync_delay` | 0 bis 120 | ms | LipSync-Verzögerung |
| `number.nad_main_trigger1_delay` | 0 bis 15 | s | Trigger 1 Verzögerung |
| `number.nad_main_trigger2_delay` | 0 bis 15 | s | Trigger 2 Verzögerung |
| `number.nad_main_trigger3_delay` | 0 bis 15 | s | Trigger 3 Verzögerung |

#### Tuner
| Entität | Bereich | Einheit | Beschreibung |
|---------|---------|--------|--------------|
| `number.nad_tuner_am_frequency` | 530 bis 1710 | kHz | AM-Frequenz |
| `number.nad_tuner_fm_frequency` | 87.5 bis 108.5 | MHz | FM-Frequenz |
| `number.nad_tuner_preset` | 1 bis 40 | - | Tuner-Vorwahl |
| `number.nad_tuner_xm_channel` | 0 bis 255 | - | XM-Kanal |

---

### Auswahl-Entitäten (Select)

#### Klangmodi
| Entität | Optionen | Beschreibung |
|---------|----------|--------------|
| `select.nad_main_listening_mode_analog` | None, ProLogic, PLIIMovie, PLIIMusic, NEO6Cinema, NEO6Music, EARS, EnhancedStereo, AnalogBypass | Analog-Signal Klangmodus |
| `select.nad_main_listening_mode_digital` | None, ProLogic, PLIIMovie, PLIIMusic, NEO6Cinema, NEO6Music, EARS, EnhancedStereo, StereoDownmix | Digital-Signal Klangmodus |
| `select.nad_main_listening_mode_dolby_digital` | None, PLIIMovie, PLIIMusic, SurroundEX, StereoDownmix | Dolby Digital Klangmodus |
| `select.nad_main_listening_mode_dts` | None, NEO6Music, StereoDownmix | DTS Klangmodus |

#### Lautsprecher-Konfiguration
| Entität | Optionen | Beschreibung |
|---------|----------|--------------|
| `select.nad_main_speaker_back_config2` | Small, Large | Lautsprechergröße Rückseite |
| `select.nad_main_speaker_center_config` | Off, Small, Large | Lautsprechergröße Center |
| `select.nad_main_speaker_front_config` | Small, Large | Lautsprechergröße Front |
| `select.nad_main_speaker_surround_config` | Off, Small, Large | Lautsprechergröße Surround |

#### Trigger
| Entität | Optionen | Beschreibung |
|---------|----------|--------------|
| `select.nad_main_auto_trigger` | Main, Zone2, Zone3, Zone4, All | Trigger-Eingang |
| `select.nad_main_trigger1_out` | Main, Zone2, Zone3, Zone4, Zone234, Source | Trigger 1 Ausgang |
| `select.nad_main_trigger2_out` | Main, Zone2, Zone3, Zone4, Zone234, Source | Trigger 2 Ausgang |
| `select.nad_main_trigger3_out` | Main, Zone2, Zone3, Zone4, Zone234, Source | Trigger 3 Ausgang |

#### Anzeige
| Entität | Optionen | Beschreibung |
|---------|----------|--------------|
| `select.nad_main_vfd_display` | On, Temp | VFD-Anzeige |
| `select.nad_main_vfd_line1` | MainSource, Volume, ListeningMode, AudioSourceFormat, Zone2Source, Zone3Source, Zone4Source, Off | VFD Zeile 1 |
| `select.nad_main_vfd_line2` | MainSource, Volume, ListeningMode, AudioSourceFormat, Zone2Source, Zone3Source, Zone4Source, Off | VFD Zeile 2 |
| `select.nad_main_vfd_templine` | 1, 2 | VFD Temperaturzeile |

#### Video & Tuner
| Entität | Optionen | Beschreibung |
|---------|----------|--------------|
| `select.nad_main_video_mode` | NTSC, PAL | Videomodus |
| `select.nad_tuner_band` | AM, FM, XM, DAB | Tuner-Band |
| `select.nad_tuner_digital_mode` | XM, DAB | Tuner-Digitalmodus |

---

### Sensoren

| Entität | Beschreibung |
|---------|--------------|
| `sensor.nad_dsp_version` | DSP-Version |
| `sensor.nad_uart_version` | UART-Version |
| `sensor.nad_tuner_dab_dls` | DAB DLS-Text |
| `sensor.nad_tuner_dab_service` | DAB Service-Name |
| `sensor.nad_tuner_fm_rdsname` | FM RDS Stationname |
| `sensor.nad_tuner_fm_rdstext` | FM RDS Text |
| `sensor.nad_tuner_xm_channel_name` | XM Kanalname |
| `sensor.nad_tuner_xm_name` | XM Name |
| `sensor.nad_tuner_xm_title` | XM Titel |

---

## 🎚️ Service Aufrufe

### Media Player Services

#### Lautstärke steuern
```yaml
# Lautstärke absolut setzen (0.0 bis 1.0)
service: media_player.volume_set
target:
  entity_id: media_player.nad_main
data:
  volume_level: 0.5

# Lautstärke relativ ändern
service: media_player.volume_up
target:
  entity_id: media_player.nad_main

service: media_player.volume_down
target:
  entity_id: media_player.nad_main
```

#### Ein/Aus schalten
```yaml
service: media_player.turn_on
target:
  entity_id: media_player.nad_main

service: media_player.turn_off
target:
  entity_id: media_player.nad_main
```

#### Stummschaltung
```yaml
service: media_player.volume_mute
target:
  entity_id: media_player.nad_main
data:
  is_volume_muted: true  # oder false
```

#### Quelle auswählen
```yaml
service: media_player.select_source
target:
  entity_id: media_player.nad_main
data:
  source: "TV"  # oder Quellenname/Nummer
```

#### Klangmodus auswählen
```yaml
service: media_player.select_sound_mode
target:
  entity_id: media_player.nad_main
data:
  sound_mode: "PLIIMovie"
```

---

### Switch Services

#### Schalter umschalten
```yaml
# Einschalten
service: switch.turn_on
target:
  entity_id: switch.nad_speaker_sub

# Ausschalten
service: switch.turn_off
target:
  entity_id: switch.nad_speaker_sub

# Umschalten
service: switch.toggle
target:
  entity_id: switch.nad_speaker_sub
```

---

### Number Services

#### Wert setzen
```yaml
service: number.set_value
target:
  entity_id: number.nad_main_bass
data:
  value: 5.0
```

---

### Select Services

#### Option auswählen
```yaml
service: select.select_option
target:
  entity_id: select.nad_main_listening_mode_digital
data:
  option: "PLIIMovie"
```

---

## 📊 YAML Automatisierungsbeispiele

### Beispiel 1: Lautstärke bei Abwesenheit reduzieren
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

### Beispiel 3: Klangmodus für Filme
```yaml
automation:
  - alias: "Film-Modus für Netflix"
    trigger:
      - platform: state
        entity_id: media_player.tv
        to: "Netflix"
    action:
      - service: media_player.select_sound_mode
        target:
          entity_id: media_player.nad_main
        data:
          sound_mode: "PLIIMovie"
```

### Beispiel 4: Subwoofer nachts ausschalten
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

### Beispiel 5: Lautstärke basierend auf Tageszeit
```yaml
automation:
  - alias: "Lautstärke begrenzen nachts"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.nad_main_bass
        data:
          value: 0  # Bass auf 0 setzen
      - service: number.set_value
        target:
          entity_id: number.nad_main_treble
        data:
          value: 0  # Höhen auf 0 setzen

  - alias: "Lautstärke normalisieren morgens"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.nad_main_bass
        data:
          value: 5  # Bass auf 5 setzen
      - service: number.set_value
        target:
          entity_id: number.nad_main_treble
        data:
          value: 5  # Höhen auf 5 setzen
```

---

## 🔍 Fehlerbehebung

### Häufige Probleme & Lösungen

| Problem | Ursache | Lösung |
|---------|---------|--------|
| **Verbindung kann nicht hergestellt werden** | Falscher Port/IP | Port/IP prüfen, Gerät einschalten |
| **Befehle werden nicht unterstützt** | Älteres Modell | Nur verfügbare Entitäten werden angezeigt |
| **Lautstärke funktioniert nicht** | Falsche Min/Max-Werte | Optionen in der Integration anpassen |
| **Entitäten werden nicht angezeigt** | Deaktiviert oder nicht unterstützt | In Einstellungen → Entitäten aktivieren |

### Debug-Logging aktivieren

Fügen Sie in `configuration.yaml` hinzu:

```yaml
logger:
  default: info
  logs:
    custom_components.nad: debug
    nad_receiver: debug
```

Dann Home Assistant neu starten und Logs prüfen.

---

## 📝 Wichtige Befehle

### Power & Grundfunktionen
- `Main.Power?` → `Main.Power=On` oder `Main.Power=Off`
- `Main.Power=On` → Einschalten
- `Main.Power=Off` → Ausschalten

### Lautstärke
- `Main.Volume?` → `Main.Volume=-30` (aktueller Wert in dB)
- `Main.Volume=-25` → Lautstärke auf -25 dB setzen
- `Main.Volume+` → Lautstärke erhöhen
- `Main.Volume-` → Lautstärke verringern

### Stummschaltung
- `Main.Mute?` → `Main.Mute=On` oder `Main.Mute=Off`
- `Main.Mute=On` → Stummschaltung aktivieren
- `Main.Mute=Off` → Stummschaltung deaktivieren

### Quelle
- `Main.Source?` → `Main.Source=3` (Quellen-Nummer)
- `Main.Source=2` → Quelle 2 auswählen
- `Source1.Name?` → Name der Quelle 1
- `Source1.Enabled?` → `Source1.Enabled=Yes` oder `No`

### Klangmodus
- `Main.ListeningMode?` → Aktueller Klangmodus
- `Main.ListeningMode=PLIIMovie` → Klangmodus setzen

### Modell & Version
- `Main.Model?` → Modellname (z.B. "T 758")
- `Main.Version?` → Firmware-Version

---

## 🔧 Optionen anpassen

Nach der Installation können Sie die Optionen anpassen:

1. **Einstellungen** → **Geräte & Dienste**
2. **NAD Integration** auswählen
3. **Optionen** → **Einstellungen**
4. Werte anpassen:
   - **Minimale Lautstärke (dB):** Standard -92
   - **Maximale Lautstärke (dB):** Standard -20
   - **Lautstärkeschritt:** Standard 4

---

## 📚 Unterstützte NAD-Modelle

Die Integration sollte mit den meisten NAD-Receivern funktionieren, die das RS-232-Protokoll oder Netzwerksteuerung unterstützen, darunter:

- NAD T 758, T 777, T 787
- NAD C 356, C 375, C 388, C 390
- NAD M17
- Und viele weitere...

**Hinweis:** Nicht alle Modelle unterstützen alle Befehle. Die Integration passt sich automatisch an.

---

## 🔗 Nützliche Links

- [GitHub Repository](https://github.com/rrooggiieerr/homeassistant-nad)
- [Home Assistant Community](https://community.home-assistant.io/)
- [NAD Electronics](https://nadelectronics.com/)
- [HACS](https://hacs.xyz/)

---

## 📞 Support

- **GitHub Issues:** [Issues](https://github.com/rrooggiieerr/homeassistant-nad/issues)
- **GitHub Discussions:** [Discussions](https://github.com/rrooggiieerr/homeassistant-nad/discussions)
- **Home Assistant Forum:** [Forum](https://community.home-assistant.io/)

---

*Diese Schnellübersicht wurde für die deutsche Home Assistant Community erstellt. Letzte Aktualisierung: 2024*
