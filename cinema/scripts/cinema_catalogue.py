"""Catalogue des sorties films/séries/anime depuis TMDB -> data/catalogue.json.
Usage : python -I backend/v-cinema/scripts/cinema_catalogue.py [--sortie FICHIER] [--fixture DOSSIER] [--pages N]
  [--films-avant 90] [--films-apres 180] [--series-jours 365]   (fenêtre de dates, en jours)
Clé : variable d'environnement TMDB_API_KEY (clé « API Key » v3 gratuite). Jamais dans un fichier ni un commit.
  --fixture DOSSIER : lit des réponses TMDB enregistrées au lieu d'appeler le réseau (tests, sans clé).
Ce que ça fait : films à l'affiche et à venir en France, séries en cours de diffusion ; détaille chacun (durée, genres) ;
  classe « anime » ce qui est animé (genre 16) et en japonais. N'écrit que des données publiques TMDB (pas de secret).
Le catalogue est REMPLACÉ à chaque exécution ; le journal de Simon (journal.json) n'est jamais touché.
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinema_lib as lib

API = 'https://api.themoviedb.org/3'
RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
LISTES = [('movie', 'movie/now_playing'), ('movie', 'movie/upcoming'), ('tv', 'tv/on_the_air')]


class Source:
    """Appelle TMDB, ou relit des réponses enregistrées (fixture) : fichier = chemin avec / remplacés par _ + .json."""
    def __init__(self, fixture=None, cle=None):
        self.fixture, self.cle = fixture, cle

    def get(self, chemin, **params):
        if self.fixture:
            nom = chemin.replace('/', '_') + (f"_p{params['page']}" if 'page' in params else '') + '.json'
            return lib.lire_json(os.path.join(self.fixture, nom), {})
        params.setdefault('region', 'FR')
        params = {k: v for k, v in params.items() if v is not None}   # region=None : pas de filtre de pays
        params.update(api_key=self.cle, language='fr-FR')
        url = f"{API}/{chemin}?" + urllib.parse.urlencode(params)
        for essai in range(3):
            time.sleep(0.03)
            try:
                with urllib.request.urlopen(url, timeout=20) as r: return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 404: return {}
                if e.code == 429 and essai < 2: time.sleep(2 + 3 * essai); continue
                raise SystemExit(f"TMDB a répondu {e.code} pour {chemin} (clé invalide ou quota). Arrêt sans rien écrire.")


def genres_par_id(src):
    g = {}
    for t in ('movie', 'tv'):
        for x in src.get(f'genre/{t}/list').get('genres', []): g[x['id']] = x['name']
    return g


def fiche_depuis_details(type_tmdb, tid, det, genre_ids, noms):
    """Fiche du catalogue à partir de la réponse détaillée de TMDB (None si le titre n'a pas de nom ou de date)."""
    anime = 16 in genre_ids and det.get('original_language') == 'ja'
    if type_tmdb == 'movie':
        duree, date_s, titre = det.get('runtime') or None, det.get('release_date') or None, det.get('title')
    else:
        ep = det.get('episode_run_time') or []
        duree, date_s, titre = (ep[0] if ep else None), det.get('first_air_date') or None, det.get('name')
    if not titre or not date_s: return None
    return {
        'id': f'tmdb-{type_tmdb}-{tid}',
        'type': 'anime' if anime else ('film' if type_tmdb == 'movie' else 'serie'),
        'titre': titre,
        'annee': int(date_s[:4]),
        'sortie': date_s,
        'duree_min': duree,
        'saisons': det.get('number_of_seasons') if type_tmdb == 'tv' else None,
        'genres': [noms.get(i, str(i)) for i in genre_ids],
        'affiche': det.get('poster_path') or None,
        'tmdb': {'type': type_tmdb, 'id': tid},
    }


def construire(src, pages, films_avant=90, films_apres=180, series_jours=365):
    """Garde les films sortis depuis films_avant jours ou prévus dans films_apres jours, et les séries commencées depuis series_jours jours.
    (TMDB renvoie aussi des ressorties et des séries de plusieurs décennies : ce ne sont pas des sorties.)"""
    noms = genres_par_id(src)
    auj = date.today()
    films_min, films_max = (auj - timedelta(films_avant)).isoformat(), (auj + timedelta(films_apres)).isoformat()
    series_min = (auj - timedelta(series_jours)).isoformat()
    vus, sortie = set(), []
    for type_tmdb, liste in LISTES:
        for page in range(1, pages + 1):
            for r in src.get(liste, page=page).get('results', []):
                cle = (type_tmdb, r['id'])
                if cle in vus: continue
                vus.add(cle)
                det = src.get(f'{type_tmdb}/{r["id"]}')
                if not det: continue
                genre_ids = [x['id'] for x in det.get('genres', [])] or r.get('genre_ids', [])
                fiche = fiche_depuis_details(type_tmdb, r['id'], det, genre_ids, noms)
                if not fiche: continue
                date_s = fiche['sortie']
                if type_tmdb == 'movie' and not (films_min <= date_s <= films_max): continue
                if type_tmdb == 'tv' and date_s < series_min: continue
                sortie.append(fiche)
    sortie.sort(key=lambda t: (t['sortie'], t['titre']), reverse=True)
    return sortie


def main():
    lib.utf8_console()
    a = sys.argv[1:]
    def opt(nom, defaut=None): return a[a.index(nom) + 1] if nom in a else defaut
    fixture, pages = opt('--fixture'), int(opt('--pages', 2))
    chemin = opt('--sortie', os.path.join(RACINE, 'data', 'catalogue.json'))
    cle = os.environ.get('TMDB_API_KEY', '').strip()
    if not fixture and not cle: raise SystemExit("TMDB_API_KEY absente : définis la variable d'environnement (voir PROCEDURE_CINEMA.md).")
    titres = construire(Source(fixture, cle), pages, int(opt('--films-avant', 90)), int(opt('--films-apres', 180)), int(opt('--series-jours', 365)))
    if not titres: raise SystemExit('Aucun titre reçu : le catalogue existant est conservé.')
    lib.ecrire_json(chemin, {'genere_le': lib.aujourdhui(), 'mention': 'This product uses the TMDB API but is not endorsed or certified by TMDB.', 'titres': titres})
    print(f'{len(titres)} titres écrits dans {chemin}')


if __name__ == '__main__':
    main()
