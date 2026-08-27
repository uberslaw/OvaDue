"""Map messy HP ship-to addresses onto a stable office name."""

from __future__ import annotations

# (needle in address, canonical office). Longer needles are tried first.
_OFFICE_NEEDLES: tuple[tuple[str, str], ...] = (
    ("ho chi minh city", "Ho Chi Minh City"),
    ("newcastle upon tyne", "Newcastle"),
    ("frankfurt am main", "Frankfurt"),
    ("san francisco", "San Francisco"),
    ("petaling jaya", "Petaling Jaya"),
    ("johannesburg", "Johannesburg"),
    ("marina bay", "Singapore"),
    ("miami beach", "Miami"),
    ("hong kong", "Hong Kong"),
    ("hongkong", "Hong Kong"),
    ("cape town", "Cape Town"),
    ("new york", "New York"),
    ("san diego", "San Diego"),
    ("los angeles", "Los Angeles"),
    ("southampton", "Southampton"),
    ("birmingham", "Birmingham"),
    ("manchester", "Manchester"),
    ("edinburgh", "Edinburgh"),
    ("nottingham", "Nottingham"),
    ("copenhagen", "Copenhagen"),
    ("amsterdam", "Amsterdam"),
    ("singapore", "Singapore"),
    ("hyderabad", "Hyderabad"),
    ("bangalore", "Bengaluru"),
    ("bengaluru", "Bengaluru"),
    ("melbourne", "Melbourne"),
    ("auckland", "Auckland"),
    ("istanbul", "Istanbul"),
    ("levent istanbul", "Istanbul"),
    ("winchester", "Winchester"),
    ("sunderland", "Sunderland"),
    ("sheffield", "Sheffield"),
    ("glasgow", "Glasgow"),
    ("bristol", "Bristol"),
    ("belfast", "Belfast"),
    ("cardiff", "Cardiff"),
    ("andover", "Andover"),
    ("dublin", "Dublin"),
    ("london", "London"),
    ("leeds", "Leeds"),
    ("york", "York"),
    ("cork", "Cork"),
    ("warszawa", "Warsaw"),
    ("warsaw", "Warsaw"),
    ("krakow", "Krakow"),
    ("madrid", "Madrid"),
    ("getafe", "Madrid"),
    ("zaragoza", "Zaragoza"),
    ("berlin", "Berlin"),
    ("frankfurt", "Frankfurt"),
    ("milano", "Milan"),
    ("milan", "Milan"),
    ("penang", "Penang"),
    ("selangor", "Petaling Jaya"),
    ("gurgaon", "Gurugram"),
    ("gurugram", "Gurugram"),
    ("mumbai", "Mumbai"),
    ("perth", "Perth"),
    ("sydney", "Sydney"),
    ("adelaide", "Adelaide"),
    ("brisbane", "Brisbane"),
    ("toronto", "Toronto"),
    ("montreal", "Montreal"),
    ("calgary", "Calgary"),
    ("ottawa", "Ottawa"),
    ("austin", "Austin"),
    ("houston", "Houston"),
    ("oakland", "Oakland"),
    ("seattle", "Seattle"),
    ("boston", "Boston"),
    ("chicago", "Chicago"),
    ("newark", "Newark"),
    ("miami", "Miami"),
    ("dubai", "Dubai"),
    ("ankara", "Ankara"),
    ("jakarta selatan", "Jakarta"),
    ("dki jakarta", "Jakarta"),
    ("jakarta", "Jakarta"),
    ("bangkok", "Bangkok"),
    ("beograd", "Belgrade"),
    ("belgrade", "Belgrade"),
    ("pasig", "Pasig"),
    ("shanghai", "Shanghai"),
    ("beijing", "Beijing"),
    ("shenzhen", "Shenzhen"),
    ("guangzhou", "Guangzhou"),
    ("taipei", "Taipei"),
    ("guangzhou/广州", "Guangzhou"),
    ("千代田", "Tokyo"),
    ("富士見", "Tokyo"),
    ("上海市", "Shanghai"),
    ("北京市", "Beijing"),
    ("深圳市", "Shenzhen"),
    ("广州", "Guangzhou"),
    ("台北", "Taipei"),
    ("서울", "Seoul"),
)

_SORTED_NEEDLES = tuple(sorted(_OFFICE_NEEDLES, key=lambda pair: len(pair[0]), reverse=True))

_COUNTRY_FALLBACK = {
    "japan": "Tokyo",
    "china": "China (unmapped)",
    "south korea": "Seoul",
    "taiwan": "Taipei",
    "hong kong": "Hong Kong",
}


def extract_office(addr: object, country: object = None) -> str:
    text = "" if addr is None or (isinstance(addr, float) and str(addr) == "nan") else str(addr)
    lowered = text.casefold()
    for needle, office in _SORTED_NEEDLES:
        if needle in lowered or needle in text:
            return office
    ctry = "" if country is None else str(country).strip()
    if ctry:
        mapped = _COUNTRY_FALLBACK.get(ctry.casefold())
        if mapped:
            return mapped
        return ctry
    return "Unknown"
