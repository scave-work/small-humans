"""Base de 20 ans : les titres les plus votés de chaque année (TMDB) -> data/base/AAAA.json (un fichier par année).
Usage : python -I backend/v-cinema/scripts/cinema_base.py [--debut 2006] [--fin 2026] [--films 300] [--series 100]
          [--dossier DOSSIER] [--fixture DOSSIER] [--refaire]
Clé : variable d'environnement TMDB_API_KEY (jamais dans un fichier). --fixture : réponses enregistrées (tests, sans clé).
Pour chaque année : les N films (sortie mondiale de l'année) et M séries (première diffusion dans l'année) ayant le plus de votes ;
  anime = animé et en japonais. Même fiche que le catalogue des sorties.
Reprise : une année déjà écrite est sautée (sauf --refaire). Si TMDB refuse, le script s'arrête ; les années finies restent.
Sert à chercher un titre plus ancien et à le copier dans le journal ; ne touche jamais journal.json.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinema_lib as lib
import cinema_catalogue as cat

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PAR_PAGE = 20   # TMDB renvoie 20 résultats par page


class SourceBase(cat.Source):
    """Comme Source, mais les réponses enregistrées dépendent aussi de l'année (fichier ..._aAAAA_pN.json)."""
    def get(self, chemin, **params):
        if self.fixture and ('primary_release_year' in params or 'first_air_date_year' in params):
            annee = params.get('primary_release_year') or params.get('first_air_date_year')
            nom = chemin.replace('/', '_') + f"_a{annee}_p{params['page']}.json"
            return lib.lire_json(os.path.join(self.fixture, nom), {})
        return super().get(chemin, **params)


def titres_de_l_annee(src, noms, annee, nb_films, nb_series):
    out, vus = [], set()
    for type_tmdb, chemin, cle_annee, nb in (('movie', 'discover/movie', 'primary_release_year', nb_films),
                                             ('tv', 'discover/tv', 'first_air_date_year', nb_series)):
        garde = 0
        for page in range(1, -(-nb // PAR_PAGE) + 1):
            resultats = src.get(chemin, page=page, sort_by='vote_count.desc', region=None, **{cle_annee: annee}).get('results', [])
            if not resultats: break
            for r in resultats:
                if garde >= nb or (type_tmdb, r['id']) in vus: continue
                vus.add((type_tmdb, r['id']))
                det = src.get(f'{type_tmdb}/{r["id"]}')
                if not det: continue
                genre_ids = [x['id'] for x in det.get('genres', [])] or r.get('genre_ids', [])
                fiche = cat.fiche_depuis_details(type_tmdb, r['id'], det, genre_ids, noms)
                if fiche and fiche['annee'] == annee: out.append(fiche); garde += 1
    out.sort(key=lambda t: (t['sortie'], t['titre']), reverse=True)
    return out


def main():
    lib.utf8_console()
    a = sys.argv[1:]
    def opt(nom, defaut=None): return a[a.index(nom) + 1] if nom in a else defaut
    debut, fin = int(opt('--debut', 2006)), int(opt('--fin', 2026))
    nb_films, nb_series = int(opt('--films', 300)), int(opt('--series', 100))
    dossier, fixture = opt('--dossier', os.path.join(RACINE, 'data', 'base')), opt('--fixture')
    cle = os.environ.get('TMDB_API_KEY', '').strip()
    if not fixture and not cle: raise SystemExit("TMDB_API_KEY absente : définis la variable d'environnement (voir PROCEDURE_CINEMA.md).")
    src = SourceBase(fixture, cle)
    noms = cat.genres_par_id(src)
    for annee in range(fin, debut - 1, -1):
        chemin = os.path.join(dossier, f'{annee}.json')
        if os.path.exists(chemin) and '--refaire' not in a: print(f'{annee} : déjà écrite, sautée'); continue
        titres = titres_de_l_annee(src, noms, annee, nb_films, nb_series)
        if not titres: print(f'{annee} : aucun titre reçu, rien écrit'); continue
        lib.ecrire_json(chemin, {'annee': annee, 'genere_le': lib.aujourdhui(), 'titres': titres})
        print(f'{annee} : {len(titres)} titres')


if __name__ == '__main__':
    main()
