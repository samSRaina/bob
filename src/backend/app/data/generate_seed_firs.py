"""Generates 100 SYNTHETIC "digital FIR copy" documents, laid out in the standard
CCTNS/NCRB FIR e-format (the labeled-field structure real digitized UP Police FIRs
use), and writes them to seed_firs.json next to this script.

IMPORTANT: every name, phone number, vehicle number, and narrative below is
fictional. Station names, districts, and IPC/IT-Act section numbers are real
public facts (administrative geography, statute numbers) — nothing here is a
real citizen's data or a real case record.

Of the 100 FIRs:
  - 6 form a deliberate "crack-a-case" thread: a 3-person cyber-fraud syndicate
    operating across Lucknow, Noida (Gautam Buddh Nagar), and Gorakhpur, under
    transliteration name variants, sharing a phone and a vehicle, with
    semantically similar (not identical) modus-operandi narratives, and one
    FIR where the accused is unnamed (identifiable only by phone/MO).
  - 94 are noise: unrelated cases across other stations/crime types, engineered
    to NOT share identifiers or near-duplicate MO text with the syndicate or
    each other, so the detection engines don't produce false positives.

Run: python -m app.data.generate_seed_firs
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

random.seed(1337)  # deterministic output — reproducible across runs

STATIONS = [
    {"name": "Hazratganj", "district": "Lucknow", "zone": "Lucknow Zone"},
    {"name": "Gomti Nagar", "district": "Lucknow", "zone": "Lucknow Zone"},
    {"name": "Alambagh", "district": "Lucknow", "zone": "Lucknow Zone"},
    {"name": "Sector 20", "district": "Gautam Buddh Nagar", "zone": "Meerut Zone"},
    {"name": "Sector 58", "district": "Gautam Buddh Nagar", "zone": "Meerut Zone"},
    {"name": "Kotwali Gorakhpur", "district": "Gorakhpur", "zone": "Gorakhpur Zone"},
    {"name": "Rustampur", "district": "Gorakhpur", "zone": "Gorakhpur Zone"},
    {"name": "Kotwali Kanpur", "district": "Kanpur Nagar", "zone": "Kanpur Zone"},
    {"name": "Swaroop Nagar", "district": "Kanpur Nagar", "zone": "Kanpur Zone"},
    {"name": "Cantt Varanasi", "district": "Varanasi", "zone": "Varanasi Zone"},
    {"name": "Bhelupur", "district": "Varanasi", "zone": "Varanasi Zone"},
    {"name": "Civil Lines Prayagraj", "district": "Prayagraj", "zone": "Prayagraj Zone"},
]

FIRST_NAMES = ["Rajesh", "Suresh", "Anita", "Priya", "Vikram", "Sunil", "Meena",
               "Deepak", "Kavita", "Manoj", "Sunita", "Ramesh", "Pooja", "Ashok",
               "Neha", "Vikas", "Rekha", "Sanjay", "Geeta", "Arvind"]
LAST_NAMES = ["Verma", "Sharma", "Singh", "Yadav", "Gupta", "Mishra", "Tiwari",
              "Pandey", "Srivastava", "Chaudhary", "Rastogi", "Agarwal"]

COMPLAINANT_ADDRESSES = [
    "12 Civil Lines", "45 Nehru Nagar", "7 Model Town", "88 Vikas Puri",
    "23 Ashok Marg", "56 Rajendra Nagar", "9 Shastri Nagar", "34 Indira Nagar",
]

random_id = 0


def _next_id() -> int:
    global random_id
    random_id += 1
    return random_id


def _fir_number(station_idx: int, seq: int) -> str:
    return f"{str(station_idx).zfill(3)}/2024/{str(seq).zfill(4)}"


def _random_date() -> str:
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    hour = random.randint(6, 22)
    minute = random.choice([0, 15, 30, 45])
    return f"{day:02d}/{month:02d}/2024 {hour:02d}:{minute:02d}"


def _random_complainant() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _random_phone(exclude: set[str] | None = None) -> str:
    exclude = exclude or set()
    while True:
        p = "9" + "".join(str(random.randint(0, 9)) for _ in range(9))
        if p not in exclude:
            return p


def _random_vehicle(exclude: set[str] | None = None) -> str:
    exclude = exclude or set()
    state_codes = ["UP32", "UP78", "UP53", "UP65", "UP70"]
    while True:
        v = f"{random.choice(state_codes)}{random.choice('ABCDEFGH')}{random.choice('ABCDEFGH')}{random.randint(1000,9999)}"
        if v not in exclude:
            return v


def _render(
    *,
    district: str,
    station: str,
    fir_number: str,
    date: str,
    act_sections: str,
    complainant: str,
    complainant_address: str,
    occurrence_date: str,
    place: str,
    brief_facts: str,
    modus_operandi: str,
    accused_lines: list[str],
    property_loss: str,
    action_taken: str,
) -> str:
    accused_block = "\n".join(accused_lines) if accused_lines else "Unknown accused person(s) at large."
    return f"""FIRST INFORMATION REPORT
District: {district}
P.S.: {station}
FIR No.: {fir_number}
Date/Time of FIR: {date}
Act & Sections: {act_sections}
Complainant Name: {complainant}
Complainant Address: {complainant_address}
Date/Time of Occurrence: {occurrence_date}
Place of Occurrence: {place}
Brief Facts: {brief_facts}
Modus Operandi: {modus_operandi}
Accused Details:
{accused_block}

Property/Loss: {property_loss}
Action Taken: {action_taken}
"""


# ---------------------------------------------------------------------------
# 1) The crack-a-case syndicate — 6 linked FIRs across 3 districts
# ---------------------------------------------------------------------------
SYNDICATE_PHONE = "9876500011"           # shared across two members' FIR entries
SYNDICATE_VEHICLE = "UP32XY7788"          # shared getaway vehicle
SYNDICATE_MO_VARIANTS = [
    "Caller posed as a bank/RBI official, informed the victim of a fraudulent KYC "
    "block on their account, and instructed them to share the OTP received via SMS "
    "to 'reverse' the block — the OTP was then used to authorize a UPI transfer out "
    "of the victim's account.",
    "Accused impersonated a bank customer-care representative over phone, claimed the "
    "victim's debit card KYC had expired, and talked the victim through 'verification "
    "steps' that ended with the victim reading out the OTP, which was used to push a "
    "UPI transaction from their account.",
    "Fraud call received claiming to be from the victim's bank regarding pending KYC "
    "update; caller guided the victim to install a remote-access screen-sharing app "
    "'for verification', then used the session and a follow-up OTP to drain the "
    "linked UPI account.",
]

syndicate_entries = [
    dict(station="Hazratganj", district="Lucknow", name="Mohd. Aslam", aliases=["Guddu"], has_phone=True, has_vehicle=False, mo=0),
    dict(station="Sector 58", district="Gautam Buddh Nagar", name="Mohammad Aslaam", aliases=[], has_phone=True, has_vehicle=True, mo=1),
    dict(station="Kotwali Gorakhpur", district="Gorakhpur", name="M. Aslam", aliases=["Guddu Bhai"], has_phone=False, has_vehicle=True, mo=2),
    dict(station="Gomti Nagar", district="Lucknow", name="Irfan Qureshi", aliases=[], has_phone=False, has_vehicle=False, mo=1),
    dict(station="Sector 20", district="Gautam Buddh Nagar", name="Irfaan Qureshi", aliases=["Bhoora"], has_phone=False, has_vehicle=False, mo=0),
    # No-name FIR: only description + a shared identifier links it back to the crew
    dict(station="Rustampur", district="Gorakhpur", name=None, aliases=[], has_phone=True, has_vehicle=False, mo=2, desc="Male, approx. 28-32 years, thin build, spoke Hindi with an eastern UP accent"),
]


def build_syndicate_firs() -> list[dict]:
    items = []
    for seq, entry in enumerate(syndicate_entries, start=1):
        complainant = _random_complainant()
        accused_lines = []
        phone = SYNDICATE_PHONE if entry["has_phone"] else _random_phone()
        vehicle_line = f", vehicle {SYNDICATE_VEHICLE}" if entry["has_vehicle"] else ""
        if entry["name"]:
            alias_txt = f", alias {entry['aliases'][0]}" if entry["aliases"] else ""
            accused_lines.append(f"1) {entry['name']}{alias_txt}, phone {phone}{vehicle_line}")
        else:
            accused_lines.append(f"1) Unknown male, phone {phone}, description: {entry.get('desc', '')}")

        raw = _render(
            district=entry["district"],
            station=entry["station"],
            fir_number=_fir_number(STATIONS.index(next(s for s in STATIONS if s["name"] == entry["station"])) + 1, seq + 900),
            date=_random_date(),
            act_sections="IPC 419, 420, 468, 471; IT Act 66C, 66D",
            complainant=complainant,
            complainant_address=random.choice(COMPLAINANT_ADDRESSES),
            occurrence_date=_random_date(),
            place=f"Complainant's residence, {entry['station']}",
            brief_facts=(
                "Complainant reported an unauthorized UPI debit from their savings account "
                "shortly after receiving a call from an unknown number regarding their bank KYC."
            ),
            modus_operandi=SYNDICATE_MO_VARIANTS[entry["mo"]],
            accused_lines=accused_lines,
            property_loss=f"Rs. {random.randint(30, 95) * 1000} fraudulently transferred via UPI.",
            action_taken="Case registered under Cyber Cell coordination; call detail records requisitioned.",
        )
        items.append({"raw_text": raw, "station_hint": entry["station"], "_note": "syndicate-thread"})
    return items


# ---------------------------------------------------------------------------
# 2) Noise FIRs — 94 unrelated cases, varied crime types, no shared identifiers
# ---------------------------------------------------------------------------
# Each category carries SEVERAL structurally different MO phrasings (not just a filled-in
# blank in one fixed sentence). This matters: the MO-similarity engine measures semantic
# closeness, and near copy-paste text across unrelated noise FIRs was producing spurious
# giant "false syndicates" purely from template reuse, drowning out the real signal. Real
# case narratives vary in structure even for the same crime type; the seed data now does too.
NOISE_TEMPLATES = [
    {
        "category": "Theft",
        "sections": "IPC 379, 380",
        "brief": "Complainant reported that unknown person(s) broke the lock of their {place_noun} and "
                 "stole valuables including jewellery and cash while the house was unattended.",
        "mo_variants": [
            "Accused targeted an unoccupied {place_noun} during {time_desc}, forcing open the "
            "{entry_point} before making off with the stolen items.",
            "The {place_noun} was broken into while empty; entry was gained via the {entry_point}, "
            "and movable valuables were removed before the household returned.",
            "Unidentified individual(s) forced the {entry_point} of the {place_noun} during "
            "{time_desc} and fled with property before being noticed by neighbours.",
        ],
        "loss": "Jewellery and cash worth approximately Rs. {amt}.",
        "action": "Case registered, dog squad and fingerprint team requisitioned.",
        "place_noun_options": ["residence", "shop", "godown"],
        "time_desc_options": ["early morning hours", "late night", "a festival holiday when the house was locked", "the afternoon while residents were at work"],
        "entry_point_options": ["rear window", "main door lock", "backyard grille", "terrace door"],
    },
    {
        "category": "Assault",
        "sections": "IPC 323, 341, 506",
        "brief": "Complainant alleged that the accused, following a prior dispute, physically assaulted "
                 "them and issued threats of dire consequences in the presence of witnesses.",
        "mo_variants": [
            "Accused confronted the complainant near a {place_noun} over a {dispute_reason} and "
            "assaulted them before being separated by bystanders.",
            "Following a heated exchange about a {dispute_reason}, the accused physically attacked "
            "the complainant at the {place_noun} in view of onlookers.",
            "A long-running disagreement over a {dispute_reason} escalated when the accused waylaid "
            "the complainant near the {place_noun} and struck them repeatedly.",
        ],
        "loss": "No property loss; complainant sustained minor injuries, medico-legal exam conducted.",
        "action": "Case registered, accused summoned for questioning.",
        "place_noun_options": ["market", "residence", "workplace", "local tea stall"],
        "dispute_reason_options": ["boundary wall", "loan repayment", "family land dispute", "parking spot"],
    },
    {
        "category": "Extortion",
        "sections": "IPC 384, 506",
        "brief": "Complainant, a local shop owner, reported receiving repeated calls demanding protection "
                 "money with threats of harm to their business if payment was not made.",
        "mo_variants": [
            "Accused made anonymous calls from unregistered numbers demanding {payment_desc} "
            "from the {place_noun}, threatening vandalism if refused.",
            "A caller claiming affiliation with a local group repeatedly pressured the owner of the "
            "{place_noun} for {payment_desc} under threat of business disruption.",
            "The complainant received a series of threatening calls insisting on {payment_desc} "
            "from the {place_noun}, with warnings of consequences for non-payment.",
        ],
        "loss": "No payment made; complainant reported before any transfer occurred.",
        "action": "Case registered, call tracing initiated.",
        "place_noun_options": ["shop", "business establishment", "roadside dhaba", "transport depot", "wholesale stall", "petrol pump"],
        "payment_desc_options": ["periodic cash payments", "a one-time lump-sum payment", "weekly protection money", "a fixed monthly 'fee'"],
    },
    {
        "category": "Narcotics",
        "sections": "NDPS Act 8, 20",
        "brief": "Acting on a tip-off, a police patrol intercepted an individual carrying a suspicious "
                 "package near {place_noun}, which on inspection was found to contain a narcotic substance.",
        "mo_variants": [
            "Accused was found transporting a concealed narcotic package {conveyance} during a "
            "routine checkpoint near the {place_noun}.",
            "A tip-off led a patrol team to intercept the accused carrying narcotics {conveyance} "
            "close to the {place_noun}.",
            "During a routine vehicle check near the {place_noun}, officers recovered a concealed "
            "narcotic package {conveyance} from the accused's possession.",
        ],
        "loss": "Approx. {amt2} grams of suspected narcotic substance seized.",
        "action": "Sample sent to FSL for confirmation; accused taken into custody.",
        "place_noun_options": ["bus stand", "railway crossing", "highway checkpoint", "toll plaza", "interstate border post", "market chowk"],
        "conveyance_options": ["on a two-wheeler", "in a parked car", "hidden inside a travel bag", "concealed under vegetables in a handcart"],
    },
    {
        "category": "Missing Person",
        "sections": "General Diary - Missing Person",
        "brief": "Complainant reported that a family member has been missing since the previous "
                 "evening and has not returned home or answered phone calls.",
        "mo_variants": [
            "N/A - missing person case, no known modus operandi. Last seen leaving {place_noun} "
            "wearing {clothing}.",
            "N/A - missing person case. Family last had contact by phone before the person went "
            "silent after leaving {place_noun}; was last seen wearing {clothing}.",
            "N/A - missing person case. Neighbours reported seeing the person near {place_noun} "
            "before contact was lost; description on record notes {clothing}.",
        ],
        "loss": "N/A.",
        "action": "Missing person report circulated to nearby stations; CCTV footage being reviewed.",
        "place_noun_options": ["home", "college", "workplace", "railway station", "local market"],
        "clothing_options": ["a blue shirt and dark trousers", "a grey kurta", "a school uniform", "a red saree", "a black jacket"],
    },
    {
        "category": "Cyber Fraud",
        "sections": "IPC 420; IT Act 66D",
        "brief": "Complainant reported losing money after clicking a link in a message advertising an "
                 "investment scheme with unusually high returns.",
        "mo_variants": [
            "Accused ran an online investment scam via {channel}, collecting an upfront "
            "'registration fee' from victims before going unreachable.",
            "A {channel} advertisement promising guaranteed high returns led the victim to a "
            "fraudulent trading platform where deposited funds could never be withdrawn.",
            "The accused posed as a {persona} on {channel} and convinced the victim to transfer "
            "funds into an account that turned out to be fraudulent.",
            "Victim was added to a {channel} group promoted as an exclusive trading community, and "
            "after initial small 'profits' were shown, was persuaded to deposit a larger sum that "
            "was never returned.",
        ],
        "loss": "Rs. {amt} paid as registration/investment fee.",
        "action": "Case registered, bank account freeze request sent to nodal officer.",
        "place_noun_options": ["online"],
        "channel_options": ["a messaging app", "a social-media page", "a video-call group", "an unsolicited SMS link"],
        "persona_options": ["stock-market advisor", "mutual-fund agent", "crypto trading mentor", "bank relationship manager"],
    },
    {
        "category": "Robbery",
        "sections": "IPC 392, 397",
        "brief": "Complainant reported being stopped by two unidentified individuals on a motorcycle "
                 "who snatched their bag at knifepoint before fleeing the scene.",
        "mo_variants": [
            "Accused operated in pairs on a motorcycle, targeting pedestrians walking alone near the "
            "{place_noun} during {time_desc}.",
            "Two individuals on a two-wheeler intercepted the complainant close to the {place_noun} "
            "during {time_desc} and forcibly took belongings before speeding away.",
            "The accused pair trailed the complainant from the {place_noun} during {time_desc} and "
            "snatched their bag at a secluded stretch before fleeing on a motorcycle.",
        ],
        "loss": "Handbag containing cash and a mobile phone, total value approx. Rs. {amt}.",
        "action": "Case registered, area CCTV footage being reviewed.",
        "place_noun_options": ["street", "park", "bus stop", "market lane", "flyover underpass", "colony gate"],
        "time_desc_options": ["evening hours", "late night", "early morning", "dusk"],
    },
]


def _fill(template: str, **kwargs) -> str:
    return template.format(**kwargs)


def build_noise_firs(count: int) -> list[dict]:
    items = []
    used_phones: set[str] = {SYNDICATE_PHONE}
    used_vehicles: set[str] = {SYNDICATE_VEHICLE}
    # Guard against the small name pool (20 x 12 = 240 combos) accidentally producing
    # two unrelated noise suspects with the EXACT same name — that would show up as a
    # spurious 1.00-confidence "repeat offender" in the demo with no real story behind
    # it. Near-miss phonetic collisions (different names that happen to sound alike)
    # are left in on purpose — they're a realistic, honestly-lower-confidence signal.
    used_accused_names: set[str] = set()
    # Same guard, for MO text: a finite filler-option pool means random.choice will
    # eventually produce two LITERALLY IDENTICAL MO narratives in the same category —
    # which the MO-similarity engine correctly (and unhelpfully) scores at cosine 1.0,
    # creating a false "syndicate" out of two unrelated noise cases. No similarity
    # threshold can fix an exact duplicate; uniqueness has to be enforced at generation.
    used_mo_texts_by_category: dict[str, set[str]] = defaultdict(set)

    # Round-robin the category order (shuffled once, then cycled and reshuffled each lap)
    # instead of pure random.choice — otherwise a few categories get drawn far more than
    # others purely by chance (seen: Robbery x20 vs Assault x8 out of 94), which stresses
    # each category's MO-text uniqueness pool far more unevenly than necessary.
    category_cycle: list[dict] = []

    def _next_template() -> dict:
        nonlocal category_cycle
        if not category_cycle:
            category_cycle = list(NOISE_TEMPLATES)
            random.shuffle(category_cycle)
        return category_cycle.pop()

    for i in range(count):
        station = random.choice(STATIONS)
        template = _next_template()
        complainant = _random_complainant()
        amt = random.randint(5, 60) * 1000
        amt2 = random.randint(50, 900)

        # Sample (variant + every filler slot, including place_noun) together, retrying
        # until the resulting MO text hasn't been used yet in this category. `brief` is
        # rendered from the SAME fill_kwargs so it stays consistent with the MO text.
        category = template["category"]
        seen = used_mo_texts_by_category[category]
        fill_kwargs: dict[str, str] = {}
        mo_text = None
        for _attempt in range(40):
            fill_kwargs = {"place_noun": random.choice(template["place_noun_options"])}
            if "time_desc_options" in template:
                fill_kwargs["time_desc"] = random.choice(template["time_desc_options"])
            if "entry_point_options" in template:
                fill_kwargs["entry_point"] = random.choice(template["entry_point_options"])
            if "dispute_reason_options" in template:
                fill_kwargs["dispute_reason"] = random.choice(template["dispute_reason_options"])
            if "clothing_options" in template:
                fill_kwargs["clothing"] = random.choice(template["clothing_options"])
            if "channel_options" in template:
                fill_kwargs["channel"] = random.choice(template["channel_options"])
            if "persona_options" in template:
                fill_kwargs["persona"] = random.choice(template["persona_options"])
            if "payment_desc_options" in template:
                fill_kwargs["payment_desc"] = random.choice(template["payment_desc_options"])
            if "conveyance_options" in template:
                fill_kwargs["conveyance"] = random.choice(template["conveyance_options"])
            variant = random.choice(template["mo_variants"])
            # A variant only uses the filler slots it actually references — pass every
            # known slot but ignore the ones this string doesn't have a {placeholder} for.
            usable_kwargs = {k: v for k, v in fill_kwargs.items() if "{" + k + "}" in variant}
            candidate = _fill(variant, **usable_kwargs)
            if candidate not in seen:
                mo_text = candidate
                break
        if mo_text is None:  # pool truly exhausted (shouldn't happen with these pool sizes) — accept the last try
            mo_text = candidate
        seen.add(mo_text)

        brief = _fill(template["brief"], place_noun=fill_kwargs["place_noun"])
        loss = _fill(template["loss"], amt=amt, amt2=amt2) if ("{amt" in template["loss"]) else template["loss"]

        # ~55% of noise FIRs name an accused with fresh, non-colliding identifiers;
        # the rest have no identified accused at all (also realistic).
        accused_lines: list[str] = []
        if random.random() < 0.55 and template["category"] != "Missing Person":
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            attempts = 0
            while name in used_accused_names and attempts < 20:
                name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                attempts += 1
            used_accused_names.add(name)
            phone = _random_phone(exclude=used_phones)
            used_phones.add(phone)
            line = f"1) {name}, phone {phone}"
            if random.random() < 0.3:
                vehicle = _random_vehicle(exclude=used_vehicles)
                used_vehicles.add(vehicle)
                line += f", vehicle {vehicle}"
            accused_lines.append(line)

        station_idx = STATIONS.index(station) + 1
        raw = _render(
            district=station["district"],
            station=station["name"],
            fir_number=_fir_number(station_idx, i + 1),
            date=_random_date(),
            act_sections=template["sections"],
            complainant=complainant,
            complainant_address=random.choice(COMPLAINANT_ADDRESSES),
            occurrence_date=_random_date(),
            place=f"{fill_kwargs['place_noun']}, {station['name']}",
            brief_facts=brief,
            modus_operandi=mo_text,
            accused_lines=accused_lines,
            property_loss=loss,
            action_taken=template["action"],
        )
        items.append({"raw_text": raw, "station_hint": station["name"], "_note": f"noise-{template['category']}"})
    return items


def main() -> None:
    syndicate = build_syndicate_firs()
    noise = build_noise_firs(100 - len(syndicate))
    all_items = syndicate + noise
    random.shuffle(all_items)  # interleave so ingestion order doesn't hint at the answer

    out_path = Path(__file__).parent / "seed_firs.json"
    out_path.write_text(json.dumps({"stations": STATIONS, "firs": all_items}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(all_items)} FIRs ({len(syndicate)} syndicate + {len(noise)} noise) to {out_path}")


if __name__ == "__main__":
    main()
