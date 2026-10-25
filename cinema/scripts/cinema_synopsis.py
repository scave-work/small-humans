"""Récupère le synopsis (résumé en français, TMDB) de chaque titre de la base et du journal -> cinema/data/synopsis/AAAA.json
(un fichier par année de sortie, {"id": "résumé"}). Le site charge le fichier de l'année à l'ouverture d'une fiche.
Usage : python -I backend/v-cinema/scripts/cinema_synopsis.py [--site DOSSIER_SITE] [--a-sec]
  --site : dossier cinema/ du dépôt public (défaut : ../small-humans/cinema, à côté de ce dépôt)
Clé : variable d'environnement TMDB_API_KEY (jamais dans un fichier). Relancer reprend : seuls les titres sans synopsis sont demandés.
--a-sec : compte ce qui reste à récupérer, sans appeler TMDB ni rien écrire. Ne touche ni journal.json ni la base.
"""
import glob, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinema_lib as lib
import cinema_catalogue as cat

ICI = os.path.dirname(os.path.abspath(__file__))
# dans le dépôt public le script est dans cinema/scripts ; dans le dépôt privé, le site est à côté (../small-humans/cinema)
SITE = os.path.normpath(os.path.join(ICI, '..')) if os.path.isdir(os.path.join(ICI, '..', 'data', 'base')) else os.path.normpath(os.path.join(ICI, '..', '..', '..', '..', 'small-humans', 'cinema'))


def ecrire(chemin, donnees):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, 'w', encoding='utf-8') as f: json.dump(donnees, f, ensure_ascii=False, sort_keys=True, indent=0)


def titres_connus(site):
    """{id: (annee, type_tmdb, id_tmdb)} pour la base (data/base/*.json) et les journaux."""
    out = {}
    sources = glob.glob(os.path.join(site, 'data', 'base', '*.json')) + [os.path.join(site, 'data', 'journal.json'), os.path.join(site, 'data', 'catalogue.json'), os.path.join(ICI, '..', 'data', 'journal.json')]
    for chemin in sources:
        d = lib.lire_json(chemin, {})
        for f in (d.get('titres', []) if isinstance(d, dict) else d):
            t = f.get('tmdb')
            if t and f.get('annee'): out[f['id']] = (int(f['annee']), t['type'], t['id'])
    return out


def main():
    lib.utf8_console()
    a = sys.argv[1:]
    site = a[a.index('--site') + 1] if '--site' in a else SITE
    dossier = os.path.join(site, 'data', 'synopsis')
    connus = titres_connus(site)
    existants = {}
    for annee in {v[0] for v in connus.values()}:
        existants[annee] = lib.lire_json(os.path.join(dossier, f'{annee}.json'), {})
    reste = [(i, v) for i, v in connus.items() if i not in existants[v[0]]]
    print(f'{len(connus)} titres connus, {len(reste)} synopsis à récupérer.')
    if '--a-sec' in a or not reste: return
    cle = os.environ.get('TMDB_API_KEY', '').strip()
    if not cle: raise SystemExit("TMDB_API_KEY absente : définis la variable d'environnement (voir PROCEDURE_CINEMA.md).")
    src = cat.Source(None, cle)
    sale = set()
    try:
        for n, (i, (annee, type_tmdb, tid)) in enumerate(sorted(reste, key=lambda x: -x[1][0]), 1):
            texte = (src.get(f'{type_tmdb}/{tid}', region=None).get('overview') or '').strip()
            existants[annee][i] = texte   # chaîne vide = TMDB n'a pas de résumé en français (on ne redemande pas)
            sale.add(annee)
            if n % 100 == 0:
                for an in sale: ecrire(os.path.join(dossier, f'{an}.json'), existants[an])
                sale.clear(); print(f'{n} / {len(reste)}')
    finally:
        for an in sale: ecrire(os.path.join(dossier, f'{an}.json'), existants[an])
    print('Terminé.')


if __name__ == '__main__':
    main()
