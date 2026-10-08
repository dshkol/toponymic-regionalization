# Street dominance: is San Francisco ruled by a few long streets? (2026-10-08)

A side question from Dmitry, off the regionalization line. The intuition: SF feels
dominated by a handful of long streets (Mission, Van Ness, Geary); is that unusual
among North American grid cities, or is every city like that?

Code: `side/street_dominance.py` (numbers, `side/out/street-dominance.json`) and
`side/plot_street_dominance.py` (figure, `side/out/street-dominance.png`).

## Thought experiment first

"Concentrated on a few major streets" mixes two separate claims, and only one of
them is interesting.

1. **Commerce sits on a small part of the street network.** This is close to a law
   of cities: shops cluster on arterials and main streets because that is where the
   passing trade and the zoning are. It should hold everywhere, so on its own it is
   the trivial part.
2. **The streets that carry it are few, long, and continuous under one name.**
   This depends on how a city names and lays out its arterials. A grid with an
   arterial every half mile (Chicago) spreads commerce over many parallel streets;
   a city whose arterials are a few old roads with one name end to end (Toronto's
   concession roads, SF's Mission and Geary) can concentrate it on a few.

So the metric needs a null that absorbs claim 1: the null used here is street
length. If storefronts were spread evenly along every named street, each street's
share of storefronts would equal its share of named road length. Dominance is how
far a city departs from that, and "long-street dominance" is how much more of the
storefront total goes to streets reaching at least halfway across the city
(half the side of a square of the city's area) than their share of length.

## Data and choices

- Overture places and road segments, release 2026-08-19.0, the pinned extracts of
  `pipeline/fetch_overture.py`, clipped to city limits from Overture divisions
  (SF county land, Vancouver locality, Chicago locality, Toronto county).
- Storefronts: places with confidence at least 0.5, not permanently closed, whose
  Overture `basic_category` is food, drink, retail or personal service (regex in
  the script). All places are reported too; the conclusions do not change.
- Each place goes on the street named in its own address, not the nearest line, so
  a corner cafe counts for the street it gives as its address. 91 to 93% of
  storefronts match a named street inside city limits.
- One street per normalized name, directional words dropped: N and S Western Ave are
  one street, Queen St W and E are one, West and East Broadway are one, W 4th and
  E 4th Ave are one. Bloor and Danforth stay two because they have two names.
  Naming is part of the question, so this is a choice, not a nuisance.

## Result (storefronts)

| | area km² | storefronts | half of storefronts on | top 5 streets hold | long streets hold storefronts / length |
|---|---|---|---|---|---|
| San Francisco | 122 | 15,145 | 6.7% of street length (26 streets) | 18% on 3.0% of length | 21% / 12% (1.7x) |
| Vancouver | 137 | 9,988 | 5.4% (14 streets) | 27% on 3.0% | 56% / 53% (1.1x) |
| Chicago | 607 | 32,494 | 7.6% (28 streets) | 16% on 2.5% | 74% / 66% (1.1x) |
| Toronto | 666 | 31,145 | 5.2% (22 streets) | 24% on 2.4% | 49% / 14% (3.5x) |

The trivial part is confirmed: in all four cities half of storefronts sit on 5 to
8% of named street length, and the concentration curves against length nearly
coincide (Gini against length 0.77 to 0.83). Every city is like that.

SF is not the outlier on the interesting part either. By raw top-5 share it is
third of four, behind Vancouver (Broadway, Main, Granville, Hastings, Robson) and
Toronto (Yonge, Queen, Bloor, Dundas, Eglinton). The city that best fits the
"a few long streets rule" picture is Toronto: 75 streets that reach halfway across
the city are 14% of its named street length and carry 49% of its storefronts. SF
is second (1.7x). In Chicago and Vancouver nearly every street is long, because
they are grids with continuous names, so long streets get storefronts roughly in
proportion to their length and length tells you nothing.

Scale check: in equal 4 km windows wholly inside each city, the top three streets
hold about half of the window's storefronts everywhere (medians SF 0.49, Vancouver
0.51, Chicago 0.50, Toronto 0.55). What does differ is how little street those
three occupy: 3.9% of the window's named length in SF against 5.7%, 6.9% and 9.3%.
So SF's main streets are thin corridors in a dense mesh of short residential
streets, and much of SF's top ten is neighbourhood strips 3 to 5 km long (Fillmore,
Union, Polk, Clement, 24th) rather than city-spanning roads. Mission and Geary
are the exceptions that make the impression.

## Reading

Not trivial in the second sense, but SF is not unique: Toronto is the clearer
case, and the property is mostly about naming and road history (long arterials
with one name end to end in a non-grid fabric), not about grids versus non-grids.
A usable "street dominance" metric is the long-street ratio (storefront share over
length share on streets that span the city), reported beside the length-null
concentration curve, which is the baseline every city shares.

## Caveats

- Overture category and address quality differ between the US and Canadian
  extracts (operating status is almost never filled in Vancouver and Toronto).
- The storefront filter is a regex over Overture's basic categories; home-service
  and office addresses are excluded from the headline but included under "all".
- "Reaches halfway across the city" uses a street's bounding box, which credits a
  diagonal (Milwaukee, Kingsway) and penalizes a street broken into far-apart pieces
  under one name only slightly.
- Residents (the other distribution Dmitry floated) are not done here; a
  population layer is not in the pinned extracts.
- The SF places extract refetched today matches the manifest's row count (60,536)
  but not its checksum; segments and divisions in all cities match. The manifest
  was left as it was.
