"""Tests for validate.py. Run:  py -3.13 -m unittest test_validate -v

Each test reproduces one way the ledger has been, or could be, wrong. The two
"regression" tests are the real bugs found on 2026-09-09.
"""
import unittest
from validate import validate, base

# Minimal set lists in the shape of set_names.json: [name, number, rarity]
SETNAMES = {
    'sm2':   [['Wailord', '30', 'Rare'], ['Alolan Vulpix', '21', 'Common']],          # Guardians Rising
    'sm5':   [['Alolan Vulpix', '30', 'Common'], ['Wailord', '99', 'Rare']],          # Ultra Prism
    'sm115': [['Starmie GX', '14', 'Rare Holo GX']],                                  # Hidden Fates
    'sma':   [['Sudowoodo', 'SV20', 'Rare Shiny']],                                   # Hidden Fates Shiny Vault
    'cel25': [['Pikachu', '5', 'Rare Holo']],
    'cel25c':[['Dark Gyarados', '8', 'Classic Collection']],
    'sv1':   [['Gardevoir ex', '86', 'Double Rare'], ['Gardevoir ex', '228', 'Ultra Rare']],
    # 4-element entries carry the card's attacks and abilities (set_names.json format since 2026-09-09)
    'svp':   [['Eevee', '43', 'Promo', ['Call for Family', 'Tackle']]],
}


def card(n, name, set_, num, cm_id, cm_exp, cm_name=None, trend=1.0, **extra):
    c = dict(n=n, name=name, set=set_, num=num, cm_id=cm_id, cm_exp=cm_exp,
             cm_name=cm_name if cm_name is not None else f"{name} [Attack]", trend=trend, hist={})
    c.update(extra)
    return c


def row(n, setid, number):
    return {str(n): dict(n=str(n), setid=setid, number=number)}


class GoodLedger(unittest.TestCase):
    def test_clean_ledger_passes(self):
        b = [card(31, 'Wailord (Dive)', 'Guardians Rising', '30', 297492, 1800, 'Wailord [Dive | Open Sea]')]
        fails, warns = validate(b, row(31, 'sm2', '30'), SETNAMES)
        self.assertEqual(fails, [])
        self.assertEqual(warns, [])


class RegressionWailordGRI30(unittest.TestCase):
    """Real bug: Guardians Rising filed as sm5 (Ultra Prism). Number 30 there is Alolan Vulpix,
    so Alolan Vulpix's Cardmarket product (315961) was matched under Wailord's name."""

    def test_wrong_set_code_is_caught_by_set_list(self):
        b = [card(31, 'Wailord (Dive)', 'Guardians Rising', '30', 315961, 2065, 'Alolan Vulpix [Roar | Icy Snow]')]
        fails, _ = validate(b, row(31, 'sm5', '30'), SETNAMES)
        self.assertTrue(any("is 'Alolan Vulpix' in the set list" in f for f in fails), fails)

    def test_wrong_product_is_caught_by_name_even_with_right_set_code(self):
        b = [card(31, 'Wailord (Dive)', 'Guardians Rising', '30', 315961, 1800, 'Alolan Vulpix [Roar | Icy Snow]')]
        fails, _ = validate(b, row(31, 'sm2', '30'), SETNAMES)
        self.assertTrue(any("Cardmarket product is 'Alolan Vulpix" in f for f in fails), fails)


class RegressionSudowoodoShinyVault(unittest.TestCase):
    """Real bug: Hidden Fates Shiny Vault Sudowoodo was placed in Cardmarket expansion 3856
    while Hidden Fates itself is 2514. Cardmarket folds the Shiny Vault into Hidden Fates,
    so the two must match. Name and number checks pass, only the parent rule catches it."""

    def test_subset_in_other_expansion_than_parent_fails(self):
        b = [card(22, 'Starmie GX', 'Hidden Fates', '14', 396597, 2514, 'Starmie GX [Attack]'),
             card(16, 'Sudowoodo (shiny)', 'Hidden Fates Shiny Vault', 'SV20', 551396, 3856, 'Sudowoodo [Roadblock | Rock Throw]')]
        cards = {**row(22, 'sm115', '14'), **row(16, 'sma', 'SV20')}
        fails, _ = validate(b, cards, SETNAMES)
        self.assertTrue(any('sub-set sma uses expansion [3856] but parent sm115 uses [2514]' in f for f in fails), fails)

    def test_subset_in_parent_expansion_passes(self):
        b = [card(22, 'Starmie GX', 'Hidden Fates', '14', 396597, 2514, 'Starmie GX [Attack]'),
             card(16, 'Sudowoodo (shiny)', 'Hidden Fates Shiny Vault', 'SV20', 396772, 2514, 'Sudowoodo [Roadblock | Rock Throw]')]
        cards = {**row(22, 'sm115', '14'), **row(16, 'sma', 'SV20')}
        fails, _ = validate(b, cards, SETNAMES)
        self.assertEqual(fails, [])


class RegressionEeveePromos(unittest.TestCase):
    """Real slip: four Cardmarket promos are all called 'Eevee'. The set list knew promo 43
    (Call for Family / Tackle); the product matched was 'Eevee [Call for Family | Gnaw]', a
    different 2025 promo. Name and number checks pass; only the attacks tell them apart."""

    def test_same_name_different_attacks_fails(self):
        b = [card(1, 'Eevee', 'SV Promos', '43', 826138, 5241, 'Eevee [Call for Family | Gnaw]')]
        fails, _ = validate(b, row(1, 'svp', '43'), SETNAMES)
        self.assertTrue(any('attacks/abilities on Cardmarket product' in f for f in fails), fails)

    def test_matching_attacks_pass(self):
        b = [card(1, 'Eevee', 'SV Promos', '43', 715757, 5241, 'Eevee [Call for Family | Tackle]')]
        fails, _ = validate(b, row(1, 'svp', '43'), SETNAMES)
        self.assertEqual(fails, [])

    def test_subset_of_attacks_passes(self):
        # Cardmarket sometimes lists fewer attacks than the card has
        b = [card(1, 'Eevee', 'SV Promos', '43', 715757, 5241, 'Eevee [Tackle]')]
        fails, _ = validate(b, row(1, 'svp', '43'), SETNAMES)
        self.assertEqual(fails, [])

    def test_no_bracket_or_no_attacks_is_not_checked(self):
        b = [card(1, 'Eevee', 'SV Promos', '43', 715757, 5241, 'Eevee')]
        fails, _ = validate(b, row(1, 'svp', '43'), SETNAMES)
        self.assertEqual(fails, [])
        b = [card(1, 'Pikachu', 'Celebrations', '5', 100, 4347, 'Pikachu [Thunderbolt]')]   # cel25 entry has no attacks
        fails, _ = validate(b, row(1, 'cel25', '5'), SETNAMES)
        self.assertEqual(fails, [])


class ProductMapCheck(unittest.TestCase):
    PM = {'297492': {'setid': 'sm2', 'number': '30', 'conf': 'high'},
          '315961': {'setid': 'sm5', 'number': '30', 'conf': 'high'}}

    def test_agreeing_map_passes(self):
        b = [card(31, 'Wailord (Dive)', 'Guardians Rising', '30', 297492, 1800, 'Wailord [Dive | Open Sea]')]
        fails, warns = validate(b, row(31, 'sm2', '30'), SETNAMES, product_map=self.PM)
        self.assertEqual(fails, []); self.assertEqual(warns, [])

    def test_disagreeing_map_fails(self):
        # ledger claims sm2 30 but the stored product is mapped to sm5 30 (the Wailord/Alolan Vulpix bug seen from the map side)
        b = [card(31, 'Wailord (Dive)', 'Guardians Rising', '30', 315961, 1800, 'Wailord [Dive | Open Sea]')]
        fails, _ = validate(b, row(31, 'sm2', '30'), SETNAMES, product_map=self.PM)
        self.assertTrue(any('products_map.json says product 315961 is sm5 30' in f for f in fails), fails)

    def test_product_missing_from_map_only_warns(self):
        b = [card(31, 'Wailord (Dive)', 'Guardians Rising', '30', 999999, 1800, 'Wailord [Dive | Open Sea]')]
        fails, warns = validate(b, row(31, 'sm2', '30'), SETNAMES, product_map=self.PM)
        self.assertEqual(fails, []); self.assertTrue(any('not in products_map' in w for w in warns), warns)

    def test_no_map_given_skips_check(self):
        b = [card(31, 'Wailord (Dive)', 'Guardians Rising', '30', 315961, 1800, 'Wailord [Dive | Open Sea]')]
        fails, warns = validate(b, row(31, 'sm2', '30'), SETNAMES)
        self.assertEqual(warns, [])


class OtherHardChecks(unittest.TestCase):
    def test_two_expansions_for_one_set_code_fails(self):
        b = [card(1, 'Pikachu', 'Celebrations', '5', 100, 4347), card(2, 'Pikachu', 'Celebrations', '5', 101, 4345)]
        cards = {**row(1, 'cel25', '5'), **row(2, 'cel25', '5')}
        fails, _ = validate(b, cards, SETNAMES)
        self.assertTrue(any('maps to several Cardmarket expansions' in f for f in fails), fails)

    def test_missing_price_fails(self):
        b = [card(1, 'Pikachu', 'Celebrations', '5', 100, 4347, trend=None)]
        fails, _ = validate(b, row(1, 'cel25', '5'), SETNAMES)
        self.assertTrue(any('no trend price' in f for f in fails), fails)

    def test_number_missing_from_set_list_fails(self):
        b = [card(1, 'Pikachu', 'Celebrations', '99', 100, 4347)]
        fails, _ = validate(b, row(1, 'cel25', '99'), SETNAMES)
        self.assertTrue(any('not found in set list' in f for f in fails), fails)

    def test_shared_product_id_for_different_cards_fails(self):
        b = [card(1, 'Pikachu', 'Celebrations', '5', 100, 4347),
             card(2, 'Dark Gyarados', 'Celebrations: Classic Collection', '8', 100, 4347)]
        cards = {**row(1, 'cel25', '5'), **row(2, 'cel25c', '8')}
        fails, _ = validate(b, cards, SETNAMES)
        self.assertTrue(any('appears in rows' in f for f in fails), fails)

    def test_same_card_twice_must_be_one_row_with_qty(self):
        b = [card(19, 'Dark Gyarados (Classic)', 'Celebrations: Classic Collection', '8', 576775, 4347, 'Dark Gyarados [Final Beam | Ice Beam]'),
             card(27, 'Dark Gyarados (Classic)', 'Celebrations: Classic Collection', '8', 576775, 4347, 'Dark Gyarados [Final Beam | Ice Beam]')]
        cards = {**row(19, 'cel25c', '8'), **row(27, 'cel25c', '8')}
        fails, _ = validate(b, cards, SETNAMES)
        self.assertTrue(any('merge them into one row with qty 2' in f for f in fails), fails)

    def test_qty_two_on_one_row_passes(self):
        b = [card(19, 'Dark Gyarados (Classic)', 'Celebrations: Classic Collection', '8', 576775, 4347, 'Dark Gyarados [Final Beam | Ice Beam]', qty=2)]
        fails, _ = validate(b, row(19, 'cel25c', '8'), SETNAMES)
        self.assertEqual(fails, [])

    def test_bad_qty_fails(self):
        for bad in (0, -1, 1.5, '2', True):
            b = [card(1, 'Pikachu', 'Celebrations', '5', 100, 4347, qty=bad)]
            fails, _ = validate(b, row(1, 'cel25', '5'), SETNAMES)
            self.assertTrue(any('qty must be' in f for f in fails), (bad, fails))

    def test_card_count_mismatch_fails(self):
        b = [card(1, 'Pikachu', 'Celebrations', '5', 100, 4347)]
        cards = {**row(1, 'cel25', '5'), **row(2, 'cel25', '5')}
        fails, _ = validate(b, cards, SETNAMES)
        self.assertTrue(any('card count' in f for f in fails), fails)

    def test_product_name_falls_back_to_product_list(self):
        b = [card(1, 'Pikachu', 'Celebrations', '5', 100, 4347, cm_name='')]
        fails, _ = validate(b, row(1, 'cel25', '5'), SETNAMES, products={100: {'name': 'Pikachu [Thunder]'}})
        self.assertEqual(fails, [])


class SoftChecks(unittest.TestCase):
    def test_short_gap_jump_warns(self):
        b = [card(1, 'Pikachu', 'Celebrations', '5', 100, 4347, hist={'2026-09-01': 1.0, '2026-09-09': 4.0})]
        _, warns = validate(b, row(1, 'cel25', '5'), SETNAMES)
        self.assertTrue(any('more than 3x' in w for w in warns), warns)

    def test_long_gap_jump_does_not_warn(self):
        b = [card(1, 'Pikachu', 'Celebrations', '5', 100, 4347, hist={'2024-12-30': 1.0, '2026-06-17': 4.0})]
        _, warns = validate(b, row(1, 'cel25', '5'), SETNAMES)
        self.assertEqual(warns, [])

    def test_verify_tag_warns_until_verified(self):
        b = [card(1, 'Pikachu', 'Celebrations', '5', 100, 4347, verify=True)]
        _, warns = validate(b, row(1, 'cel25', '5'), SETNAMES)
        self.assertTrue(any('tagged verify' in w for w in warns), warns)
        b[0]['verified'] = True
        _, warns = validate(b, row(1, 'cel25', '5'), SETNAMES)
        self.assertEqual(warns, [])


class NameNormalisation(unittest.TestCase):
    def test_suffixes_and_punctuation_are_ignored(self):
        self.assertEqual(base('Gyarados GX promo'), base('Gyarados-GX'))
        self.assertEqual(base('Solrock IR'), base('Solrock'))
        self.assertEqual(base('Zekrom TG'), base('Zekrom'))
        self.assertEqual(base('Ditto V (shiny)'), base('Ditto V'))
        self.assertEqual(base('Dark Gyarados (Classic) #2'), base('Dark Gyarados'))
        self.assertEqual(base('Origin Forme Dialga V promo'), base('Origin Forme Dialga V'))

    def test_different_cards_stay_different(self):
        self.assertNotEqual(base('Wailord'), base('Wailord V'))
        self.assertNotEqual(base('Crobat V'), base('Crobat VMAX'))
        self.assertNotEqual(base('Regigigas'), base('Regigigas VSTAR'))


if __name__ == '__main__':
    unittest.main()
