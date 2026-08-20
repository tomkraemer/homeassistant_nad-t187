
# Alle Major-Changes ...
... beginnend mit der Code-Übernahme von 

## Version v1.0.0 - [Dev: 18.08.26 / Dok: 20.08.26]
### 1. Umstellung auf zwei Controller, je einer pro Zone.
Bisher gab es genau einen Controller für diese NAD-Entity. Damit waren aber die beiden für mich nötigen Zonen *Main* und *Zone2* nicht sauber abgebildet. Ein Setzten der `zone`-Eigenschaft innerhalb der Media-Player-Instanzen führte zu gegenseitigem Überschreiben, da ein gemeinsamer Controller geteilt wurde. Damit gab es zwar in gewisser weise schon irgenwie zwei Mediaplayer, andererseits aber doch nur einen, da beide sich einen Controller teilten, der Status-Updates etc. für beide ohne weitere Differenzierung durchführte.
Ziel war somit, dass *Zone2*, wie schon *Main* je wie ein __eigener MediaPlayer__ auftreten soll. 


| Datei | Änderung | Grund |
| --- | --- | --- |
| `__init__.py` | `zone`-Parameter in `__init__` <br> `power.state` für jede Zone <br>  `async_setup_entry` baut 2 spez. crdntr <br> `async_unload_entry` mit spez. coordinator <br> | Zonenkennung für jeden Coordinator <br> Nutzung des zugeh. Coordinators  |
| `media_player.py` | `__init__` Jede Zone hat ihre Kennung <br> `async_setup_entry` initialisiert je ein Coordinator pro Zone und erstellt eine Instanz pro Zone  | Kein Überschreiben mehr |
| `__init__.py` <br>`media_player.py` | aus den Laufzeitdaten muss der jeweilge coordinator gezogen werden | Kein Überschreiben mehr |
| `number.py`  <br> `select.py`  <br>`sensor.py`  <br>`switch.py`  | `coordinator: NADReceiverCoordinator = config_entry.runtime_data["Main"]` | Zone "Main" wird beim setup als zugeh. coordinator gesetzt |


### 2. Vermeidung von Timeouts in `__init__.py`
Timeouts können in der Kommunikation mit dem AVR gelegentlich auftreten (z. B. bei langsamer serieller Verbindung) 

Sie werden nun bewusst ignoriert, aber als Debug-Info geloggt, um den normalen Flow nicht zu unterbrechen. 

Rückgabe: None 

### 3. Multi-Responses suber verarbeiten
Bei schneller Commandabfolge, z.B. wenn Lautstärkeanpassungen via Remote gesendet werden, konnen diese innerhalb einer Statusabfrage dazu führen, dass sowohl der Status, als auch die angepasste Lautstärke im Response stehen. NAD kann alles nur einem Kommunikator zuordnen (kennt nur einen)  gibt alles zurück.<br>
Alle Antworten werden empfangen, aber alle nicht zur Anfrage gehörenden werden ignoriert/verworfen. 

### 4. Deploy Task in `VS-Code`
überträt vioa `<CTRL><SHIFT><B>` Files 
- von `/Users/tom/Coding/Codeberg/homeassistant_nad-t187/custom_components/nad/` 
- nach `/Volumes/config/custom_components/nad/`  *[smb-Mount -> Finder `<CTRL><K>`)]*

