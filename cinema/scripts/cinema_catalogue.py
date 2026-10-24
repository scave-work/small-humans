"""Catalogue des sorties films/séries/anime depuis TMDB -> data/catalogue.json.
Usage : python -I backend/v-cinema/scripts/cinema_catalogue.py [--sortie FICHIER] [--fixture DOSSIER] [--pages N]
Clé : variable d'environnement TMDB_API_KEY (clé « API Key » v3 gratuite). Jamais dans un fichier ni un commit.
  --fixture DOSSIER : lit des réponses TMDB enregistrées au lieu d'appeler le réseau (tests, sans clé).
Ce que ça fait : films à l'affiche et à venir en France, séries en cours de diffusion ; détaille chacun (durée, genres) ;
  classe « anime » ce qui est animé (genre 16) et en japonais. N'écrit que des données publiques TMDB (pas de secret).
Le catalogue est REMPLACÉ à chaque exécution ; le journal de Simon (journal.json) n'est jamais touché.
"""
import json, os, sys, time, urllib.parse, urllib.request
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
        params.update(api_key=self.cle, language='fr-FR', region='FR')
        url = f"{API}/{chemin}?" + urllib.parse.urlencode(params)
        for essai in range(3):
            try:
                with urllib.request.urlopen(url, timeout=20) as r: return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429 and essai < 2: time.sleep(2 + 3 * essai); continue
                raise SystemExit(f"TMDB a répondu {e.code} pour {chemin} (clé invalide ou quota). Arrêt sans rien écrire.")
        time.sleep(0.05)


def genres_par_id(src):
    g = {}
    for t in ('movie', 'tv'):
        for x in src.get(f'genre/{t}/list').get('genres', []): g[x['id']] = x['name']
    return g


def construire(src, pages):
    noms = genres_par_id(src)
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
                anime = 16 in genre_ids and det.get('original_language') == 'ja'
                if type_tmdb == 'movie':
                    duree, date_s = det.get('runtime') or None, det.get('release_date') or None
                    titre = det.get('title')
                else:
                    ep = det.get('episode_run_time') or []
                    duree, date_s = (ep[0] if ep else None), det.get('first_air_date') or None
                    titre = det.get('name')
                if not titre: continue
                sortie.append({
                    'id': f'tmdb-{type_tmdb}-{r["id"]}',
                    'type': 'anime' if anime else ('film' if type_tmdb == 'movie' else 'serie'),
                    'titre': titre,
                    'annee': int(date_s[:4]) if date_s else None,
                    'sortie': date_s,
                    'duree_min': duree,
                    'saisons': det.get('number_of_seasons') if type_tmdb == 'tv' else None,
                    'genres': [noms.get(i, str(i)) for i in genre_ids],
                    'affiche': det.get('poster_path') or None,
                    'tmdb': {'type': type_tmdb, 'id': r['id']},
                })
    sortie.sort(key=lambda t: (t['sortie'] or '9999', t['titre']))
    return sortie


def main():
    lib.utf8_console()
    a = sys.argv[1:]
    def opt(nom, defaut=None): return a[a.index(nom) + 1] if nom in a else defaut
    fixture, pages = opt('--fixture'), int(opt('--pages', 2))
    chemin = opt('--sortie', os.path.join(RACINE, 'data', 'catalogue.json'))
    cle = os.environ.get('TMDB_API_KEY', '').strip()
    if not fixture and not cle: raise SystemExit("TMDB_API_KEY absente : définis la variable d'environnement (voir PROCEDURE_CINEMA.md).")
    titres = construire(Source(fixture, cle), pages)
    if not titres: raise SystemExit('Aucun titre reçu : le catalogue existant est conservé.')
    lib.ecrire_json(chemin, {'genere_le': lib.aujourdhui(), 'mention': 'This product uses the TMDB API but is not endorsed or certified by TMDB.', 'titres': titres})
    print(f'{len(titres)} titres écrits dans {chemin}')


if __name__ == '__main__':
    main()
