# ShelfCraft - Designer knižnice (Python MVP)

Python verze Unity projektu - interaktivní návrhář knihovny.
Cozy verze pro předmět Programovanie v Pythone.

## Co už funguje (MVP skeleton)
- Pygame okno 1280x720, 60 FPS
- Stelaž na 5 polic (config v JSON)
- Kniha co lepi na myš, drag&drop
- Fantom: ZELENÝ = validní místo, ČERVENÝ = kolize / mimo polici
- Ovládání: Q = horizontálně (ležící), E = vertikálně (stojící), R = otočení 90°
- LKM = položit knihu
- SQLite ukládání přes SQLAlchemy (data/shelfcraft.db)

## Technologické oblasti (3+)
1. GUI - Pygame
2. Databáze - SQLite + SQLAlchemy
3. Skriptování/files - pathlib, JSON config, Pillow export

## Jak spustit v PyCharm / VS Code

### PyCharm (doporučeno pro tebe)
1. Open -> vyber složku shelfcraft
2. PyCharm nabídne vytvořit venv - dej OK
3. Otevři Terminal dole a napiš: pip install -r requirements.txt
4. Pravý klik na src/main.py -> Run

### VS Code
1. Open Folder -> shelfcraft
2. Ctrl+` (terminal) -> pip install -r requirements.txt
3. F5 nebo python src/main.py

### Příkazová řádka
```
pip install -r requirements.txt
python src/main_physics.py
```

## Ovládání v prototypu
- Pohyb myší = pohyb knihy
- Q = horizontální režim (ležící, jako stoh)
- E = vertikální režim (stojící)
- R = otočit
- LKM = položit (jen když je zelený fantom)
- S = uložit projekt do DB
- L = načíst poslední projekt
- ESC = konec
