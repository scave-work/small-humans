"""Outils communs du journal cinéma : lecture/écriture JSON, validation d'une fiche, contrôle des secrets.
Python 3.9, bibliothèque standard seulement. Aucun secret ici : la clé TMDB vient de la variable d'environnement TMDB_API_KEY.
"""
import json, os, re, sys
from datetime import date

TYPES = {'film', 'serie', 'anime'}
STATUTS = {'vu', 'a_voir'}
ENVIES = {'hate', 'pourquoi_pas', 'un_jour'}
# La source de visionnage (cinéma, plateforme, torrent) n'est jamais enregistrée : décision de Simon, 2026-10-25.
CHAMPS = {'id', 'type', 'titre', 'annee', 'statut', 'date_vu', 'note', 'commentaire', 'envie', 'genres',
          'duree_min', 'affiche', 'tmdb', 'ajoute_le', 'maj'}
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
ID = re.compile(r'^(tmdb-(movie|tv)-\d+|manuel-[a-z0-9-]{1,60})$')
SECRETS = re.compile(r'[\w.+-]+@[\w-]+\.[a-z]{2,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|gh[ousr]_[A-Za-z0-9]{20,}|'
                     r'AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY|Bearer\s+[A-Za-z0-9._-]{20,}|api_key=[0-9a-f]{20,}', re.I)


def utf8_console():
    for flux in (sys.stdout, sys.stderr):
        try: flux.reconfigure(encoding='utf-8')
        except Exception: pass


def lire_json(chemin, defaut):
    if not os.path.exists(chemin): return defaut
    with open(chemin, encoding='utf-8-sig') as f: return json.load(f)


def ecrire_json(chemin, donnees):   # fins de ligne LF, un titre par ligne pour des diffs lisibles
    os.makedirs(os.path.dirname(chemin) or '.', exist_ok=True)
    lignes = [json.dumps(t, ensure_ascii=False, sort_keys=True) for t in donnees['titres']]
    meta = {k: v for k, v in donnees.items() if k != 'titres'}
    tete = json.dumps(meta, ensure_ascii=False, sort_keys=True)[:-1]
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
        f.write(tete + (', ' if meta else '') + '"titres": [\n' + ',\n'.join(lignes) + '\n]}\n')


def aujourdhui(): return date.today().isoformat()


def valider(fiche):
    """Renvoie la liste des problèmes d'une fiche (liste vide = fiche valide)."""
    p = []
    inconnus = set(fiche) - CHAMPS
    if inconnus: p.append('champs inconnus : ' + ', '.join(sorted(inconnus)))
    if not ID.match(str(fiche.get('id', ''))): p.append('id invalide')
    if fiche.get('type') not in TYPES: p.append('type invalide (film, serie, anime)')
    if not str(fiche.get('titre', '')).strip(): p.append('titre manquant')
    if fiche.get('statut') not in STATUTS: p.append('statut invalide (vu, a_voir)')
    n = fiche.get('note')
    if n is not None and not (isinstance(n, (int, float)) and 0.5 <= n <= 5 and (n * 2) == int(n * 2)):
        p.append('note : de 0,5 à 5 par demi-étoile, ou vide')
    d = fiche.get('date_vu')
    if d is not None and not DATE.match(str(d)): p.append('date_vu : AAAA-MM-JJ')
    if fiche.get('statut') == 'vu' and not d: p.append('un titre vu a besoin de date_vu')
    e = fiche.get('envie')
    if e is not None and e not in ENVIES: p.append('envie invalide (hate, pourquoi_pas, un_jour)')
    if SECRETS.search(json.dumps(fiche, ensure_ascii=False)): p.append('texte ressemblant à un secret ou un mail')
    return p


def controle_secrets(chemins):
    """Cherche mails, jetons et clés dans des fichiers avant publication. Renvoie [(fichier, extrait)]."""
    trouves = []
    for c in chemins:
        with open(c, encoding='utf-8-sig', errors='replace') as f: texte = f.read()
        for m in SECRETS.finditer(texte): trouves.append((c, m.group(0)[:40]))
    return trouves
