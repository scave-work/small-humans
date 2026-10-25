"""Robot des ajouts musique : intègre les envois du site (musique/ajouts/*.json) dans musique/titres.json.
Mêmes règles que le script 13 de l'atelier (copiées d'ici : GENRES, ID, est_mix, SECRETS, convertir) : en cas de changement, modifier les deux.
Usage : python -I .github/scripts/ajouts_musique.py [--titres musique/titres.json] [--dossier musique/ajouts]
Affiche « N nouveaux … » ; ne supprime pas les fichiers (c'est le workflow qui le fait). Code retour 1 si un secret est détecté (rien n'est écrit).
"""
import json, os, re, sys, glob
GENRES = {'house-techno', 'electro-melodique', 'electro-pop', 'electronica', 'french-touch', 'synthwave', 'trance-psy', 'hard-edm', 'edm',
          'bass', 'dub-reggae', 'chill', 'ambient', 'neoclassique', 'ost', 'folk-world', 'hiphop', 'rock-metal', 'pop-indie', 'epic', 'funk-jazz', 'autre'}
ID = re.compile(r'^[\w-]{11}$')
MIX = re.compile(r'\b(mix|mixtape|live set|dj set|full set|boiler room|full album|full ep|1 hour|hours?|horas|lo-?fi|chillhop|study music|sleep music|relaxing music|playlist|compilation|set @)\b|\bmix\s*#\d', re.I)
VERSION = re.compile(r'\b(original|extended|radio|club|vocal|dub|instrumental|edit|re|short|album|single|cut|dance|remix)\s+(mix|version)\b|\bremix\b|\(\s*mix\s*\)', re.I)
def est_mix(t): return bool(MIX.search(VERSION.sub('', t)))   # même règle que 7_export_site_musique.py
# motifs de secrets (adresses mail, jetons GitHub/Google, clés privées) ; les mots « password » ou « secret » seuls sont des titres de morceaux
SECRETS = re.compile(r'[\w.+-]+@[\w-]+\.[a-z]{2,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|gh[ousr]_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY|Bearer\s+[A-Za-z0-9._-]{20,}', re.I)
def lire_json(chemin, defaut):
    if not os.path.exists(chemin): return defaut
    with open(chemin, encoding='utf-8-sig') as f: return json.load(f)


def ecrire_json(chemin, donnees):   # même format que 7_export_site_musique.py (indent=0), fins de ligne LF comme le dépôt
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f: json.dump(donnees, f, ensure_ascii=False, indent=0)

def convertir(x):
    """Ligne exportée par la page « À ajouter » -> ligne de titres.json (même règle d'artiste que le script 7)."""
    t = x['titre'].strip(); chaine = (x.get('artiste') or '').strip()
    if ' - ' in t:
        a, t = [s.strip() for s in t.split(' - ', 1)]; fiable = True
        if t and t.lower() in chaine.lower() and a.lower() not in chaine.lower(): a, t = t, a   # « Titre - Artiste » : la chaîne est l'artiste
    else: a, fiable = chaine, False
    g = x.get('genre') or 'autre'
    return dict(youtube=x['youtube'], titre=t, artiste=a, genre=g, tags=[g], source='ajout', artiste_fiable=fiable, mix=est_mix(x['titre']))


def main():
    a = sys.argv[1:]
    titres_p = a[a.index('--titres') + 1] if '--titres' in a else 'musique/titres.json'
    dossier = a[a.index('--dossier') + 1] if '--dossier' in a else 'musique/ajouts'
    titres = lire_json(titres_p, [])
    connus = {t['youtube'] for t in titres}
    nouveaux, doublons, invalides, sans_style = [], 0, 0, 0
    for f in sorted(glob.glob(os.path.join(dossier, '*.json'))):
        try: lignes = lire_json(f, [])
        except Exception as e: print('Illisible, ignoré :', f, e); continue
        for x in lignes if isinstance(lignes, list) else []:
            if not isinstance(x, dict) or not ID.match(str(x.get('youtube', ''))) or not str(x.get('titre', '')).strip(): invalides += 1; continue
            if x['youtube'] in connus: doublons += 1; continue
            if x.get('genre') not in GENRES: x['genre'] = 'autre'; sans_style += 1
            connus.add(x['youtube']); nouveaux.append(convertir(x))
    texte = json.dumps(nouveaux, ensure_ascii=False)
    m = SECRETS.search(texte)
    if m: print('ARRÊT : motif de secret détecté (' + m.group(0)[:30] + '…). Rien n\'est écrit.'); return 1
    print(f'{len(nouveaux)} nouveaux titres ; {doublons} déjà connus ; {invalides} lignes invalides ; {sans_style} sans style (rangés en « autre »).')
    if nouveaux: ecrire_json(titres_p, titres + nouveaux)
    return 0


if __name__ == '__main__': sys.exit(main())
