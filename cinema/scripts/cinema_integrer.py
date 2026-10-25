"""Intègre les fiches exportées par le site (ajouts_cinema_AAAA-MM-JJ.json) dans data/journal.json.
Usage : python -I backend/v-cinema/scripts/cinema_integrer.py FICHIER.json [--journal data/journal.json] [--a-sec]
Format d'un export : {"titres": [ fiche, ... ]} (ou une simple liste de fiches). Une fiche = voir cinema_lib.CHAMPS.
Règles : fiche invalide -> refusée et listée (rien n'est écrit si une seule est invalide) ; même id -> la fiche
  avec le « maj » le plus récent gagne ; une fiche de statut « retire » (bouton Retirer du site) supprime le titre du journal.
Ne fait AUCUN git et ne publie rien : le journal est copié dans le dépôt public seulement après « oui, publie ».
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinema_lib as lib

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def integrer(journal, ajouts):
    par_id = {t['id']: t for t in journal['titres']}
    nouveaux = modifies = retires = 0
    for f in ajouts:
        f.setdefault('ajoute_le', lib.aujourdhui())
        f.setdefault('maj', lib.aujourdhui())
        ancien = par_id.get(f['id'])
        if f['statut'] == 'retire':
            if ancien is not None and str(f['maj']) >= str(ancien.get('maj', '')): par_id.pop(f['id']); retires += 1
            continue
        if ancien is None: nouveaux += 1
        elif str(f['maj']) >= str(ancien.get('maj', '')): modifies += 1
        else: continue
        par_id[f['id']] = f
    journal['titres'] = sorted(par_id.values(), key=lambda t: (t.get('date_vu') or '', t.get('ajoute_le') or '', t['id']), reverse=True)
    return nouveaux, modifies, retires


def main():
    lib.utf8_console()
    a = sys.argv[1:]
    if not a or a[0].startswith('--'): raise SystemExit(__doc__)
    chemin_journal = a[a.index('--journal') + 1] if '--journal' in a else os.path.join(RACINE, 'data', 'journal.json')
    brut = lib.lire_json(a[0], [])
    ajouts = brut['titres'] if isinstance(brut, dict) else brut
    refus = [(f.get('titre', '?'), p) for f in ajouts if (p := lib.valider(f))]
    if refus:
        for titre, p in refus: print(f'REFUSÉ  {titre} : ' + ' ; '.join(p))
        raise SystemExit('Rien n\'a été écrit. Corrige les fiches ci-dessus.')
    journal = lib.lire_json(chemin_journal, {'version': 1, 'titres': []})
    n, m, r = integrer(journal, ajouts)
    if '--a-sec' in a: print(f'À sec : {n} nouveaux, {m} modifiés, {r} retirés, rien écrit.'); return
    lib.ecrire_json(chemin_journal, journal)
    print(f'{n} nouveaux, {m} modifiés, {r} retirés. Journal : {len(journal["titres"])} titres -> {chemin_journal}')


if __name__ == '__main__':
    main()
