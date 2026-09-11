# cardmarket-ledger

A price ledger for a Pokémon card collection, fed by Cardmarket's own nightly price export.
Two containers: one downloads the export every day, validates the collection and rebuilds a
static page; the other serves that page and the growing archive of daily exports.

No third-party price mirrors, no scraping, no API keys. Cardmarket publishes the file for free;
this just keeps it.

## What you get

- `binder_ledger.html`: your cards valued at Cardmarket's 30-day average (the trend jumps on
  single sales, so it is shown as a second column), a history column, sortable, dark mode. Served at http://localhost:8080.
- `data/history/price_guide_6_YYYYMMDD.json`: one copy of Cardmarket's export per day.
  Every product on Cardmarket Pokémon, about 17 MB a day. Nobody else keeps these publicly.
- A validator that refuses to build if a card is matched to the wrong product.

## Run it

Requires Docker. Python 3.13 only if you want to run the scripts outside Docker.

```
git clone https://github.com/<you>/cardmarket-ledger
cd cardmarket-ledger
mkdir data
cp example/binder.json example/cards.csv data/
docker compose up -d --build
docker compose logs -f refresh
```

The first start does a refresh immediately, then cron runs one at 06:00 every day.
Open http://localhost:8080. Every container start also refreshes, so a machine that is off at
06:00 catches up when it boots.

## Files

| File | Role |
|---|---|
| `refresh.py` | daily job: download export, save to history, ask Wayback to archive it, update prices, validate, build page |
| `validate.py` | hard checks on the collection; a FAIL rolls back and blocks the build (`test_validate.py` covers it) |
| `build_page.py` | renders `data/binder_ledger.html` from `data/binder.json` |
| `manage.py` | add, remove, set quantity or finish, mark verified. The only way to change the card set |
| `movers.py`, `movers_image.py` | after each refresh: biggest climbers and droppers among English cards (EUR 5-20 band, 7-day window, spike guard) -> `data/movers.md` (paste-ready post) and `data/movers.png` (shareable image, card pictures from pokemontcg.io) |
| `build_product_map.py` | one-time (and per new set): maps every English Cardmarket product id to set code, number, name, rarity, with a confidence grade. Output `data/products_map.json` |
| `watchlist.py` | turns the buy screen into a Cardmarket want-list import with a wanted price per line (`data/wants.txt`, split by value in `data/wants/`, summary in `wants_prices.md`) writes the daily check list of cards worth opening (`data/checklist.md`) and flags cards whose cheapest copy fell below that card's own usual floor (`data/floor_alerts.md`) |
| `Dockerfile`, `start.sh` | the refresh container: Python + cron |
| `compose.yml`, `nginx.conf` | both containers and the web server config |

Everything with state lives in `data/`:

| File | Kind |
|---|---|
| `binder.json`, `cards.csv` | your collection with Cardmarket product ids. Private, not in git. Start from `example/` |
| `set_names.json` | card lists per set from [pokemon-tcg-data](https://github.com/PokemonTCG/pokemon-tcg-data), fetched once per set |
| `cm_expansions.json` | which Cardmarket expansion id is which set, and why |
| `cm_match.json` | per-card matching record |
| `products_map.json` | **the product map**: ~22,000 Cardmarket product ids -> set, number, name, rarity, confidence. Built once, versioned, what makes the price history card-level data |
| `price_guide_6.json`, `products_singles_6.json` | today's downloads, overwritten daily |
| `history/` | the archive, one export per day |
| `binder_ledger.html` | the built page |
| `movers.md`, `movers.json`, `movers.png` | the daily movers post, its rows, and the image (`card_images/` caches the card pictures) |

`LEDGER_DATA` overrides the data folder (default `./data`).

## Adding a card

```
py -3.13 manage.py add "Mew" cel25 11 --page "Pikachu" --set-name Celebrations
py -3.13 manage.py qty 19 2
py -3.13 manage.py finish 12 reverse
py -3.13 manage.py remove 57
py -3.13 manage.py add "Lucario" sma SV22 --page Investments --bought 19.65 --pending
py -3.13 manage.py arrived 58
```

`--bought` records the price paid including shipping; the page then shows paid vs now for those
cards. `--pending` marks a card bought but not yet in hand (tag on the page), `arrived` clears it.

Set codes are pokemontcg.io's (`cel25`, `swsh12pt5`, `sv3`), see the
[card list folder](https://github.com/PokemonTCG/pokemon-tcg-data/tree/master/cards/en).
`add` checks that the number really is that card, finds the Cardmarket expansion, lists the
matching products with today's price and stops if more than one matches until you pass
`--cm-id`. Then run `refresh.py` or wait for the nightly run.

## The product map

Cardmarket identifies a card only by product id, a name like `Eevee [Call for Family | Gnaw]` and an
expansion id. `build_product_map.py` labels every English expansion id with its set (by overlapping
product names with the set's card list), then inside each expansion matches products to card numbers
by name, by attacks and abilities, and, where several versions share both, by a price fingerprint:
pokemontcg.io publishes Cardmarket prices per card number, and the product whose price history
contains that (trend, 30-day) pair is the card. Confidence per row: `high` (unique or fingerprint
with a clear runner-up), `medium` (fingerprint close call or price-rank fallback), `low` (guess).
Code cards are skipped. Japanese expansions are not mapped yet.

The validator uses the map as its strongest check: a card's stored product id must map to its own
set code and number.

## How a card is tied to a Cardmarket product

Cardmarket's export has product ids, names and expansion ids, no set names or card numbers,
and the same name recurs across sets and versions. So each card is matched once:

1. The set's card list from pokemon-tcg-data gives the name at that number.
2. Cardmarket expansion ids are labelled by overlapping their product names with that list.
   An English set and its Japanese twin both match; the one whose prices agree with an
   independent reading wins. Stored in `cm_expansions.json`.
3. Inside the expansion, the product with that name. Several versions (regular, full art,
   illustration rare) are told apart by price tier; look-alikes get a `verify` tag until checked.

Refreshing never repeats this, it looks up the stored id in the day's export.

## Data sources

- Cardmarket price export: <https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json>
  (offered on [cardmarket.com › Data › Price Guide](https://www.cardmarket.com/en/Pokemon/Data/Price-Guide))
- Cardmarket product list: <https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json>
- Card lists per set: <https://github.com/PokemonTCG/pokemon-tcg-data>
- Older exports: the [Wayback Machine](https://web.archive.org/web/*/downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json)

Page values are Cardmarket's 30-day average; "Price Trend" is kept alongside. Both are for the product as a whole (all languages
and conditions listed under it). Reverse holo rows use the export's reverse-holo fields.

## Tests

```
py -3.13 -m unittest test_validate -v
```

Also run during every image build; a failing test means no image.

## License

MIT.
